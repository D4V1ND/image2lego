# shape_server.py
from flask import Flask, request, send_file
import torch
from shap_e.diffusion.sample import sample_latents
from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
from shap_e.models.download import load_model, load_config
from shap_e.util.notebooks import decode_latent_mesh
import tempfile, io

app = Flask(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device being used for creating shapes: {device}")
xm = load_model("transmitter", device=device)
model = load_model("text300M", device=device)
diffusion = diffusion_from_config(load_config("diffusion"))

@app.route("/", methods=["POST"])
def generate():
    prompt = request.args.get("prompt")
    latents = sample_latents(
        batch_size=1,
        model=model,
        diffusion=diffusion,
        guidance_scale=15.0,
        model_kwargs={"texts": [prompt]},
        progress=True,
        clip_denoised=True,
        use_fp16=True,
        use_karras=True,
        karras_steps=64,
        sigma_min=1e-3,
        sigma_max=160,
        s_churn=0,
    )
    t = decode_latent_mesh(xm, latents[0]).tri_mesh()
    str_buf = io.StringIO()
    t.write_obj(str_buf)
    buf = io.BytesIO(str_buf.getvalue().encode("utf-8"))
    return send_file(buf, mimetype="application/octet-stream")

app.run(port=8000)