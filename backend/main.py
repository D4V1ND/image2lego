# ── Imports ───────────────────────────────────────────────────────────────────

import os                          # Lets us read settings from the computer (like environment variables)
from pathlib import Path           # Makes working with folder/file paths easy — no messy string joining
from flask import Flask, request, jsonify, send_from_directory
#   Flask             = the web server itself (like opening a restaurant)
#   request           = reads what the user sent us
#   jsonify           = turns Python data into JSON to send back
#   send_from_directory = sends a file to the user (for downloads)
from dotenv import load_dotenv     # Reads the .env file so secret settings get loaded

from integrations.shape_generator import ShapeGenerator  # Calls shape_server.py: text prompt → 3D .obj
from services.image_to_text import ImageToText           # Uses Ollama AI: image → text description
from services.obj_to_lego import ModelToLDR              # Orchestrator: .obj → .ldr (calls obj_to_ldr.py)
from services.ldr_parser import LdrParser                # Reads .ldr and returns brick/layer data as JSON

# ── Setup ─────────────────────────────────────────────────────────────────────

load_dotenv()  # Actually loads the .env file now

app = Flask(__name__)  # Creates the web server — like "turning on the restaurant"

BASE_DIR = Path(__file__).parent          # The folder where main.py lives
FRONTEND_DIR = BASE_DIR.parent / "frontend"  # Where the HTML lives
MODELS_DIR = BASE_DIR / "models"          # Where we save .obj files
LDR_OUTPUT_DIR = BASE_DIR / "ldr_output"  # Where we save .ldr files
MODELS_DIR.mkdir(exist_ok=True)           # Create the folder if it doesn't exist yet
LDR_OUTPUT_DIR.mkdir(exist_ok=True)       # exist_ok=True = don't crash if already exists

shape_gen = ShapeGenerator()    # One instance ready to generate 3D shapes for all requests
ldr_converter = ModelToLDR()    # One instance ready to convert .obj → .ldr for all requests


# ── Health check ──────────────────────────────────────────────────────────────
# Visit /health to check if the server is running. Just says "yes I'm alive".

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, "lego_front.html")

@app.route("/images/<filename>")
def serve_frontend_images(filename):
    return send_from_directory(FRONTEND_DIR / "images", filename)


# ── Step 1a: Generate 3D model from text prompt ───────────────────────────────
# User sends: { "prompt": "a red chair" }
# Server returns: { "filename": "...", "filepath": "...", "url": "...", "filesize": ... }

@app.route("/generate/from-prompt", methods=["POST"])
def generate_from_prompt():
    data = request.get_json()                    # Read the JSON the user sent
    if not data or not data.get("prompt"):
        return jsonify({"error": "Missing 'prompt' in request body"}), 400
        # 400 = "you sent a bad request" — missing required field

    prompt = data["prompt"].strip()              # Get the prompt, remove extra spaces
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    try:
        result = shape_gen.generate_model(prompt)  # Ask the AI to make a 3D shape
        return jsonify(result)                     # Send the result back as JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        # 500 = "something went wrong on our end"


# ── Step 1b: Generate text prompt from image, then generate 3D model ──────────
# User uploads an image file → AI describes it → AI generates a 3D shape from that description
# User sends: multipart form with 'image' file and optional 'prompt_type'
# Server returns: { "prompt": "...", "filename": "...", "filepath": "...", ... }

@app.route("/api/image-to-lego", methods=["POST"])
def image_to_lego():
    if "image" not in request.files:              # If no image was attached, complain
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]           # Grab the uploaded image
    prompt_type = request.form.get("prompt_type", "default")  # What kind of description to generate

    upload_path = MODELS_DIR / image_file.filename  # Where to save the image temporarily
    image_file.save(upload_path)                    # Save the uploaded image to disk

    try:
        # Step A: Image → text description using the Ollama AI
        converter = ImageToText(task_type=prompt_type)
        converter.attach_image(str(upload_path))
        prompt = converter.predict(prompt_type=prompt_type)

        # Step B: Text description → 3D .obj shape
        obj_result = shape_gen.generate_model(prompt)
        obj_result["prompt"] = prompt
        obj_result["url_obj"] = obj_result.pop("url_obj", None)  # rename 'url' → 'url_obj' for frontend

        # Step C: Convert obj to ldr
        if not obj_result.get("filepath_obj") or not Path(obj_result["filepath_obj"]).exists():
            return jsonify({"error": "OBJ file was not created"}), 500

        resolution = int(request.form.get("resolution", 64))
        ldr_result = ldr_converter.convert_to_ldr(obj_result["filepath_obj"], resolution=resolution)
        return jsonify({**obj_result, **ldr_result})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        # "finally" always runs even if there was an error
        # Delete the temp image — we don't need it anymore
        if upload_path.exists():
            upload_path.unlink()


# ── Step 2: Convert .obj to .ldr ─────────────────────────────────────────────
# User sends: { "obj_path": "/path/to/model.obj", "resolution": 64 }
# Server returns: { "ldr_file_path": "...", "url": "...", "model_id": "...", "file_size": ... }

# @app.route("/convert/obj-to-ldr", methods=["POST"])
# def convert_obj_to_ldr():
#     data = request.get_json()
#     if not data or not data.get("obj_path"):
#         return jsonify({"error": "Missing 'obj_path' in request body"}), 400

#     obj_path = data["obj_path"]
#     resolution = int(data.get("resolution", 64))   # Default resolution = 64 if not provided

#     try:
#         result = ldr_converter.convert_to_ldr(obj_path, resolution=resolution)
#         return jsonify(result)
#     except FileNotFoundError as e:
#         return jsonify({"error": str(e)}), 404     # 404 = "file not found"
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# ── Step 3: Parse .ldr into layer data for the frontend ──────────────────────
# Reads the .ldr file and returns all brick layers as JSON so the UI can display them.
# User sends: GET /ldr/layers?file=1234567890.ldr

@app.route("/ldr/layers", methods=["GET"])
def get_ldr_layers():
    filename = request.args.get("file")            # Read ?file=xxx.ldr from the URL
    if not filename:
        return jsonify({"error": "Missing 'file' query param"}), 400

    ldr_path = LDR_OUTPUT_DIR / filename
    if not ldr_path.exists():
        return jsonify({"error": f"LDR file not found: {filename}"}), 404

    parser = LdrParser(str(ldr_path))
    if not parser.parse():
        return jsonify({"error": "Failed to parse LDR file"}), 500

    return jsonify(parser.get_layers_data())       # Returns ALL layers


# Same as above but only returns layers 0 to layer_num.
# Used for step-by-step building UI — "show me only the first 5 layers"
# User sends: GET /ldr/layers/5?file=1234567890.ldr

@app.route("/ldr/layers/<int:layer_num>", methods=["GET"])
def get_ldr_layers_up_to(layer_num):
    filename = request.args.get("file")
    if not filename:
        return jsonify({"error": "Missing 'file' query param"}), 400

    ldr_path = LDR_OUTPUT_DIR / filename
    if not ldr_path.exists():
        return jsonify({"error": f"LDR file not found: {filename}"}), 404

    parser = LdrParser(str(ldr_path))
    if not parser.parse():
        return jsonify({"error": "Failed to parse LDR file"}), 500

    return jsonify(parser.get_layers_up_to(layer_num))  # Returns only layers 0..layer_num


# ── File serving ──────────────────────────────────────────────────────────────
# These routes let the frontend download files directly by URL.

@app.route("/ldr_output/<filename>", methods=["GET"])
def serve_ldr(filename):
    # Lets user download any .ldr file: GET /ldr_output/1234567890.ldr
    return send_from_directory(LDR_OUTPUT_DIR, filename)


@app.route("/models/<filename>", methods=["GET"])
def serve_model(filename):
    # Lets user download any .obj file: GET /models/a_red_chair_123.obj
    return send_from_directory(MODELS_DIR, filename)


# ── Full pipeline: prompt → obj → ldr ────────────────────────────────────────
# THE MAIN ENDPOINT — does everything in one call:
#   text prompt → 3D shape → LEGO file
# User sends: { "prompt": "a red chair", "resolution": 64 }
# Server returns: { "prompt": "...", "obj": {...}, "ldr": {...} }

@app.route("/pipeline/prompt-to-ldr", methods=["POST"])
def pipeline_prompt_to_ldr():
    data = request.get_json()
    if not data or not data.get("prompt"):
        return jsonify({"error": "Missing 'prompt'"}), 400

    prompt = data["prompt"].strip()
    resolution = int(data.get("resolution", 64))

    try:
        obj_result = shape_gen.generate_model(prompt)                              # prompt → .obj
        ldr_result = ldr_converter.convert_to_ldr(obj_result["filepath"],          # .obj → .ldr
                                                   resolution=resolution)
        return jsonify({
            "prompt": prompt,      # The original text prompt
            "obj": obj_result,     # Info about the generated .obj file
            "ldr": ldr_result,     # Info about the generated .ldr file
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Start the server ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Only runs if you start this file directly with: python main.py
    # (Not when imported by something else)
    port = int(os.getenv("FLASK_PORT", 5000))  # Read port from .env, default 5000
    app.run(debug=True, port=port, use_reloader=False)
    # use_reloader=False = fixes WinError 10038 socket crash on Windows

