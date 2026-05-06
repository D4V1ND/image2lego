# model_to_ldr.py
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class ModelToLDR:
    def __init__(self):
        # All paths are relative to this file's directory (backend/)
        self.base_dir    = Path(__file__).resolve().parents[1]
        self.obj_to_ldr  = self.base_dir / "scripts" / "obj_to_ldr.py"
        self.output_dir  = self.base_dir / "ldr_output"
        self.temp_dir    = Path(tempfile.gettempdir()) / "model_lego_temp"

        # Read from env (set in .env or shell)
        self.python_path = os.environ.get("PYTHON_PATH", sys.executable)

        # Create dirs if missing
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if not self.obj_to_ldr.exists():
            raise FileNotFoundError(f"Required script not found: {self.obj_to_ldr}")

        print(f"ModelToLDR initialized → output: {self.output_dir}")

    # ── Public entry point ────────────────────────────────────────────────────

    def convert_to_ldr(self, model_path: str, resolution: int = 128) -> dict:
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        ext = path.suffix.lower()
        print(f"Converting {ext} file to LDR: {model_path}")

        if ext == ".obj":
            return self._convert_obj_to_ldr(path, resolution)

        elif ext == ".stl":
            print("STL detected → converting to OBJ first...")
            obj_path = path.with_suffix(".obj")
            script = f"""
import trimesh
mesh = trimesh.load(r'{path}')
mesh.export(r'{obj_path}')
print('Conversion successful')
"""
            temp_script = self.temp_dir / "stl_to_obj.py"
            temp_script.write_text(script)
            result = subprocess.run([self.python_path, str(temp_script)],
                                    capture_output=True, text=True)
            print(result.stdout)
            if not obj_path.exists():
                raise RuntimeError(f"STL→OBJ failed: {result.stderr}")
            return self._convert_obj_to_ldr(obj_path, resolution)

        elif ext == ".glb":
            raise NotImplementedError("GLB→LDR is not implemented yet.")

        else:
            raise ValueError(f"Unsupported format: {ext}. Use OBJ or STL.")

    # ── Internal conversion ───────────────────────────────────────────────────

    def _convert_obj_to_ldr(self, obj_path: Path, resolution: int) -> dict:
        # Check deps
        try:
            subprocess.run(
                [self.python_path, "-c", "import numpy, trimesh, scipy, colorsys"],
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            print("Missing packages → installing...")
            subprocess.run(
                [self.python_path, "-m", "pip", "install", "numpy", "trimesh", "scipy"],
                check=True
            )

        model_id = str(int(datetime.now().timestamp() * 1000))
        output_ldr = self.output_dir / f"{model_id}.ldr"

        cmd = [self.python_path, str(self.obj_to_ldr),
               str(obj_path), str(output_ldr), str(resolution)]
        print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("stderr:", result.stderr)

        if not output_ldr.exists():
            print("LDR not created → using placeholder")
            output_ldr.write_text(self._placeholder_ldr(model_id))
            return self._make_result(output_ldr, model_id, is_placeholder=True,
                                     error="obj_to_ldr.py produced no output")

        print(f"LDR created: {output_ldr} ({output_ldr.stat().st_size} bytes)")
        return self._make_result(output_ldr, model_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_result(self, ldr_path: Path, model_id: str,
                     is_placeholder=False, error=None) -> dict:
        result = {
            "filepath_ldr": str(ldr_path),
            "url_ldr": f"/ldr_output/{ldr_path.name}",
            "model_id": model_id,
            "filesize_ldr": ldr_path.stat().st_size,
        }
        if is_placeholder:
            result["is_placeholder"] = True
            result["conversion_error"] = error
        return result

    def _placeholder_ldr(self, model_id: str) -> str:
        return f"""0 Converted Model {model_id}
0 Name: model_{model_id}.ldr
0 Author: AI Model Converter
0 !HISTORY {datetime.now().isoformat()} [AI] Generated from 3D model

1 4 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat
1 14 0 -24 0 1 0 0 0 1 0 0 0 1 3001.dat
1 14 0 -48 0 1 0 0 0 1 0 0 0 1 3003.dat
1 4 0 -72 0 1 0 0 0 1 0 0 0 1 3003.dat
"""
