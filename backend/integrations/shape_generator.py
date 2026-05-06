import os
import re 
import time
import requests 
from pathlib import Path
from dotenv import load_dotenv 

load_dotenv()


class ShapeGenerator: 
    def __init__(self): 
        self.api_endpoint = os.getenv("SHAPE_API_URL")
        self.models_dir = Path(__file__).resolve().parents[1] / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        print(f"ShapeGenerator initialized with API endpoint: {self.api_endpoint}")

    def generate_model(self, prompt: str, guidance_scale: float = 15.0, num_steps: int = 24, seed: int = None) -> dict:
        if not prompt or not prompt.strip(): 
            raise ValueError("Prompt cannot be empty")

        print(f"Generating 3D model for prompt: '{prompt}' with guidance_scale={guidance_scale} and num_steps={num_steps}")

        params = {
            "prompt": prompt,
            "guidance_scale": guidance_scale,
            "num_steps": num_steps,
        }

        if seed is not None:
            params["seed"] = seed

        safe_prompt = re.sub(r"[^a-zA-Z0-9]", "_", prompt)[:30]
        timestamp = int(time.time() * 1000)
        filename = f"{safe_prompt}_{timestamp}.obj"
        file_path = self.models_dir / filename

        try: 
            print(f"Sending request to {self.api_endpoint} with params: {params}")
            response = requests.post(self.api_endpoint, params=params, timeout=500)
            response.raise_for_status() 

            content = response.content 
            print(f"Received response with {len(content) / 1024:.1f} KB")

            if len(content) < 100:
                raise ValueError(f"Received suspiciously very small file ({len(content)} bytes)")

            file_path.write_bytes(content)
            file_size = file_path.stat().st_size

            print(f"Saved the 3D model to {file_path}")
            print(f"File size: {file_size} bytes")

            return { 
                "filename_obj": filename, 
                "filepath_obj": str(file_path),
                "url_obj": f"/models/{filename}",
                "filesize_obj": file_size,
            }

        except Exception as e: 
            print(f"Theres an error while building the 3D Model: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            raise RuntimeError(f"Error while generating the 3D Model: {e}")
        
    def better_model(self, model_num: str, instruction: str) -> dict: 
        """This method is a placeholder for future implementation of model improvement based on user instruction."""
        print("Trying to make the model better...")
        print(f"Improving the model {model_num} with {instruction}")
        try: 
            return self.generate_model(instruction)
        except Exception as e: 
            print(f"Theres an error while improving the 3D Model: {e}")
            raise RuntimeError(f"Error while improving the 3D Model: {e}")
        
    # def convert_stl_to_glb(self, stl_path: str) -> str:
    #     # Placeholder for STL to GLB conversion
    #     # In a real implementation, use a library like trimesh or a conversion service
    #     print(f"Converting STL to GLB: {stl_path}")

    #     # For now, just return the original STL path
    #     return stl_path
    def convert_stl_to_glb(self, stl_path: str) -> str:
        import trimesh

        print(f"Converting STL to GLB: {stl_path}")

        stl_path = Path(stl_path)
        if not stl_path.exists():
            raise FileNotFoundError(f"STL file not found: {stl_path}")

        glb_path = stl_path.with_suffix(".glb")

        mesh = trimesh.load(str(stl_path))
        mesh.export(str(glb_path))

        print(f"Converted to GLB: {glb_path}")
        return str(glb_path)
