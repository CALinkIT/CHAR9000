#!/usr/bin/env python3
"""Smoke-test ComfyUI: queue one SD1.5 image and wait for it. Usage: comfyui_smoke_test.py [host:port]"""
import json, sys, time, urllib.request, uuid

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost:8188"
WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 9000, "steps": 25, "cfg": 7, "sampler_name": "euler",
          "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0],
          "negative": ["7", 0], "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "SD1.5/v1-5-pruned-emaonly.safetensors"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "modern waste-to-energy facility at sunrise, clean industrial architecture, photo", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "char9000_smoke", "images": ["8", 0]}},
}

def get(path):
    return json.loads(urllib.request.urlopen(f"http://{HOST}{path}", timeout=30).read())

t0 = time.time()
req = urllib.request.Request(f"http://{HOST}/prompt", headers={"Content-Type": "application/json"},
                             data=json.dumps({"prompt": WORKFLOW, "client_id": str(uuid.uuid4())}).encode())
pid = json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]
while time.time() - t0 < 300:
    hist = get(f"/history/{pid}")
    if pid in hist:
        status = hist[pid]["status"]
        images = [i["filename"] for o in hist[pid]["outputs"].values() for i in o.get("images", [])]
        errors = [m[1].get("exception_message", "")[:200] for m in status.get("messages", []) if m[0] == "execution_error"]
        print(f"status={status.get('status_str')} images={images} seconds={time.time() - t0:.1f}" + (f" error={errors[0]}" if errors else ""))
        sys.exit(0 if images else 1)
    time.sleep(2)
sys.exit("timeout")
