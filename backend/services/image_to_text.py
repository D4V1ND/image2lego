import os
import base64
from pathlib import Path

from .prompts import PROMPT_DEFAULT, PROMPT_ENGINEERING, PROMPT_BUILDING, PROMPT_STYLE
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

PROMPTS = {
    "default": PROMPT_DEFAULT,
    "engineering": PROMPT_ENGINEERING,
    "building": PROMPT_BUILDING,
    "style": PROMPT_STYLE,
}

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

class ImageToText: 
    def __init__(self, task_type: str = "default"): 
        self.task_type = task_type
        self.image_parts: list[dict] = []

    def _get_mime_type(self, file_path: str) -> str: 
        ext = Path(file_path).suffix.lower()
        return MIME_TYPES.get(ext, "image/jpeg")
    
    def _encode_image(self, image_path: str) -> str: 
        path = Path(image_path)
        if not path.exists(): 
            raise FileNotFoundError(f"Image file not found: {image_path}")
        with open(path, "rb") as f: 
            data = base64.b64encode(f.read()).decode("utf-8")
        mime_type = self._get_mime_type(image_path)
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{data}"}}

    def attach_image(self, image_path: str): 
        self.image_parts= [self._encode_image(image_path)]

    def attach_images(self, image_paths: list[str]) -> str:
        if not image_paths:
            raise ValueError("No image paths provided")
        self.image_parts = [self._encode_image(p) for p in image_paths]
        return f"{len(self.image_parts)} images attached successfully"
    
    def _call_api(self, parts: list[dict], temperature: float = 0.4, max_tokens: int = 8192):
        self.model_name = ChatOllama(
            model = "qwen3-vl:8b", 
            temperature=temperature,
            max_new_tokens=max_tokens
        )

        message = HumanMessage(content=parts)
        response = self.model_name.invoke([message])
        return response.content
    
    def predict(self, prompt_type: str = "default", custom_prompt: str | None = None) -> str:
        if not self.image_parts:
            raise ValueError("No images attached. Please attach at least one image before calling predict.")
        prompt_text = custom_prompt or PROMPTS.get(prompt_type)
        if not prompt_text:
            raise ValueError(f"No prompt available for type: {prompt_type}")
        parts = [
            {"type": "text", "text": prompt_text}] + list(self.image_parts)
        return self._call_api(parts)
    
    def generate_text(self, prompt: str) -> str: 
        """Send a plain text prompt to Qwen3-VL without any images attached. Useful for testing text-only prompts."""
        parts = [{"type": "text", "text": prompt}]
        return self._call_api(parts)
    
    def generate_instructions(self, view_paths: list[str], original_description: str = "") -> dict: 
        if not view_paths:
            raise ValueError("No view image paths provided. Please provide at least one image path for instruction generation.")
        self.attach_images(view_paths)

        results = {"original": original_description}

        for key in ("engineering", "building", "style"): 
            base_prompt = PROMPTS[key]
            prompt = ( 
                f'The following is a description of the object: "{original_description}".\n\n{base_prompt}'
                if original_description 
                else base_prompt
            )
            results[key] = self.predict(prompt_type=key, custom_prompt=prompt)
            print(f"{key} instructions: {results[key]}" )
        
        return results

# apple_image = "images/apple.png"
# test = ImageToText()
# # To generate instructions
# # print(test.generate_instructions([apple_image], original_description="A red apple"))

# # To output text for the model API
# test.attach_image(apple_image)
# print(test.predict())
