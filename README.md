# image2lego

Convert an uploaded image into a LEGO-style LDraw model (`.ldr`).

The project uses an image model to describe the uploaded picture, generates a 3D OBJ from that description with Shap-E, voxelizes the OBJ into LEGO-sized bricks, and writes the result as an LDraw file that can be previewed or opened in LDraw-compatible tools.

## What it does

- Upload an image from the browser UI.
- Convert the image into a text prompt with Ollama (`qwen3-vl:8b`).
- Generate a 3D `.obj` model from the prompt with Shap-E.
- Convert the `.obj` mesh into stacked LEGO bricks.
- Export an `.ldr` file with LDraw part IDs and LEGO color codes.
- Serve generated `.obj` and `.ldr` files from the Flask backend.

## Project layout

```text
backend/
  main.py                         Flask app and API routes
  shape_server.py                 Local Shap-E model server
  integrations/shape_generator.py Client for the Shap-E server
  services/image_to_text.py       Image-to-prompt service using Ollama
  services/obj_to_lego.py         OBJ/STL to LDR orchestration
  services/ldr_parser.py          LDR layer parser for the frontend
  scripts/obj_to_ldr.py           Mesh voxelization and LDraw writer

frontend/
  lego_front.html                 Browser UI
  images/                         Frontend assets
```

Generated files are written to:

- `backend/models/` for uploaded/generated model files
- `backend/ldr_output/` for exported `.ldr` files
- `shap_e_model_cache/` for cached Shap-E model data

These generated artifacts are ignored by git.

## Requirements

- Python 3.10+ recommended
- Ollama running locally with the `qwen3-vl:8b` model available
- Python packages listed in `requirements.txt`

Install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

PyTorch is included in `requirements.txt`, but GPU users may want to install the CUDA-specific PyTorch wheel from the official PyTorch instructions before installing the rest of the dependencies.

Pull the Ollama vision model:

```powershell
ollama pull qwen3-vl:8b
```

## Configuration

Create a `.env` file in the project root:

```env
FLASK_PORT=5000
SHAPE_API_URL=http://127.0.0.1:8000/
```

`PYTHON_PATH` is optional. If omitted, the backend uses the current Python interpreter.

```env
PYTHON_PATH=C:\path\to\python.exe
```

## Running the app

Start the Shap-E model server first:

```powershell
python backend\shape_server.py
```

In another terminal, start the Flask backend:

```powershell
python backend\main.py
```

Open the app at:

```text
http://127.0.0.1:5000/
```

Upload an image. The backend will create an OBJ model, convert it to an LDR LEGO model, and return URLs for the generated files.

## API

### Health check

```http
GET /health
```

Returns:

```json
{ "status": "ok" }
```

### Image to LEGO

```http
POST /api/image-to-lego
```

Multipart form fields:

- `image`: uploaded image file
- `prompt_type`: optional prompt style, defaults to `default`
- `resolution`: optional voxel/build resolution, defaults to `64`

Returns generated prompt, OBJ file details, and LDR file details.

### Prompt to LDR

```http
POST /pipeline/prompt-to-ldr
```

Body:

```json
{
  "prompt": "a small red toy car",
  "resolution": 64
}
```

Runs text prompt -> OBJ -> LDR.

### LDR layers

```http
GET /ldr/layers?file=<filename>.ldr
GET /ldr/layers/<layer_num>?file=<filename>.ldr
```

Parses an exported `.ldr` file into layer data for the frontend.

### Generated files

```http
GET /models/<filename>
GET /ldr_output/<filename>
```

Downloads generated OBJ and LDR files.

## Direct OBJ to LDR conversion

You can run the converter script directly:

```powershell
python backend\scripts\obj_to_ldr.py backend\models\model.obj backend\ldr_output\model.ldr 64
```

The converter rescales the mesh, voxelizes it, fills interior layers, places common LEGO brick sizes, maps colors to LDraw color codes, and writes an `.ldr` file.

## Notes

- Higher `resolution` values create more detailed models but take longer and produce more bricks.
- The Shap-E server can run on CPU, but generation is much faster with CUDA.
- Output quality depends heavily on the image description produced by the vision model and the generated OBJ geometry.
- The project exports LDraw data, not official LEGO building instructions.
