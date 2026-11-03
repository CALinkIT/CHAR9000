#!/usr/bin/env python3
"""Point Open WebUI image generation at the local ComfyUI (FLUX.1-schnell, 1024px, 4 steps). Idempotent.
Env: OWUI_EMAIL, OWUI_PASSWORD. Optional: OWUI_URL (http://localhost:3000), COMFYUI_URL (http://host.docker.internal:8188)
Run: python scripts/owui_enable_comfyui.py   (install.ps1 runs it for you)
"""
import json, os, urllib.request

OWUI = os.environ.get("OWUI_URL", "http://localhost:3000")
COMFY = os.environ.get("COMFYUI_URL", "http://host.docker.internal:8188")
CKPT = "FLUX/flux1-schnell-fp8.safetensors"
WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 4, "cfg": 1, "sampler_name": "euler",
          "scheduler": "simple", "denoise": 1, "model": ["4", 0], "positive": ["6", 0],
          "negative": ["7", 0], "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
    "5": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "openwebui", "images": ["8", 0]}},
}
NODES = [
    {"type": "prompt", "key": "text", "node_ids": ["6"]},
    {"type": "model", "key": "ckpt_name", "node_ids": ["4"]},
    {"type": "width", "key": "width", "node_ids": ["5"]},
    {"type": "height", "key": "height", "node_ids": ["5"]},
    {"type": "steps", "key": "steps", "node_ids": ["3"]},
    {"type": "seed", "key": "seed", "node_ids": ["3"]},
]

def call(method, path, body=None, token=None):
    req = urllib.request.Request(OWUI + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"null")

token = call("POST", "/api/v1/auths/signin", {"email": os.environ.get("OWUI_EMAIL", "admin@char9000.local"),
                                               "password": os.environ["OWUI_PASSWORD"]})["token"]
cfg = call("GET", "/api/v1/images/config", token=token)
cfg.update({"ENABLE_IMAGE_GENERATION": True, "IMAGE_GENERATION_ENGINE": "comfyui",
            "IMAGE_GENERATION_MODEL": CKPT, "IMAGE_SIZE": "1024x1024", "IMAGE_STEPS": 4,
            "COMFYUI_BASE_URL": COMFY, "COMFYUI_WORKFLOW": json.dumps(WORKFLOW), "COMFYUI_WORKFLOW_NODES": NODES})
saved = call("POST", "/api/v1/images/config/update", cfg, token=token)
print("image generation:", saved["ENABLE_IMAGE_GENERATION"], "| engine:", saved["IMAGE_GENERATION_ENGINE"],
      "| model:", saved["IMAGE_GENERATION_MODEL"], "| comfyui:", saved["COMFYUI_BASE_URL"])
