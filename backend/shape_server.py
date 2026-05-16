# shape_server.py
from flask import Flask, request, send_file, jsonify
import torch
from pathlib import Path
from shap_e.diffusion.sample import sample_latents
from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
from shap_e.models.download import load_model, load_config
from shap_e.util.notebooks import decode_latent_mesh
import tempfile, io

app = Flask(__name__)

CACHE_DIR = str(Path(__file__).parent / "shap_e_model_cache")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device being used for creating shapes: {device}")
xm = load_model("transmitter", device=device, cache_dir=CACHE_DIR)
model = load_model("text300M", device=device, cache_dir=CACHE_DIR)
diffusion = diffusion_from_config(load_config("diffusion", cache_dir=CACHE_DIR))

@app.route("/", methods=["POST"])
def generate():
    prompt = request.args.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    guidance_scale = float(request.args.get("guidance_scale", 15.0))
    num_steps = int(request.args.get("num_steps", 24))

    try:
        latents = sample_latents(
            batch_size=1,
            model=model,
            diffusion=diffusion,
            guidance_scale=guidance_scale,
            model_kwargs={"texts": [prompt]},
            progress=True,
            clip_denoised=True,
            use_fp16=device.type == "cuda",
            use_karras=True,
            karras_steps=num_steps,
            sigma_min=1e-3,
            sigma_max=160,
            s_churn=0,
        )
        t = decode_latent_mesh(xm, latents[0]).tri_mesh()
        str_buf = io.StringIO()
        t.write_obj(str_buf)
        buf = io.BytesIO(str_buf.getvalue().encode("utf-8"))
        return send_file(buf, mimetype="application/octet-stream")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

app.run(port=8000)
