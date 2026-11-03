#!/usr/bin/env python3
"""CHAR9000 ComfyUI API workflows (image + video) and a smoke-test runner.

Usage:
  comfyui_workflows.py export <dir>          # write workflow JSONs
  comfyui_workflows.py test [name ...]       # queue + wait, report time/output
Env: COMFY_URL (default http://127.0.0.1:8188)
"""
import json, os, sys, time, urllib.request

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
NEG = "blurry, low quality, distorted, watermark, text"


def sdxl(prompt="a modern waste-to-energy facility at sunrise, photorealistic", seed=1):
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "SDXL/sd_xl_base_1.0.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 7.0, "sampler_name": "dpmpp_2m",
              "scheduler": "karras", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "char9000_sdxl", "images": ["8", 0]}},
    }


def flux(prompt="a modern waste-to-energy facility at sunrise, photorealistic", seed=1):
    # FLUX.1-schnell: 4 steps, cfg 1, no negative prompt
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "FLUX/flux1-schnell-fp8.safetensors"}},
        "5": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler",
              "scheduler": "simple", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "char9000_flux", "images": ["8", 0]}},
    }


def ltxv(prompt="slow aerial drone shot over a recycling facility, trucks moving, golden hour", seed=1, length=97):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "LTXV/ltx-video-2b-v0.9.1.safetensors"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5xxl_fp16.safetensors", "type": "ltxv"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 0]}},
        "5": {"class_type": "LTXVConditioning", "inputs": {"positive": ["3", 0], "negative": ["4", 0], "frame_rate": 25}},
        "6": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": 768, "height": 512, "length": length, "batch_size": 1}},
        "7": {"class_type": "LTXVScheduler", "inputs": {"steps": 30, "max_shift": 2.05, "base_shift": 0.95, "stretch": True,
              "terminal": 0.1, "latent": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1], "cfg": 3.0}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0],
               "sigmas": ["7", 0], "latent_image": ["6", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["1", 2]}},
        "13": {"class_type": "SaveWEBM", "inputs": {"images": ["12", 0], "filename_prefix": "char9000_ltxv", "codec": "vp9", "fps": 25.0, "crf": 32.0}},
    }


def wan(prompt="a worker in high-visibility PPE walking through a clean modern plant, cinematic", seed=1,
        unet="wan2.1_t2v_14B_fp8_scaled.safetensors", lora="Wan21_CausVid_14B_T2V_lora_rank32.safetensors",
        width=832, height=480, length=33):
    # CausVid LoRA lets Wan run in ~6 steps at cfg 1.0
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": 0.7}},
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 0]}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "8": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": width, "height": height, "length": length, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 6, "cfg": 1.0, "sampler_name": "uni_pc", "scheduler": "simple",
              "denoise": 1.0, "model": ["3", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["7", 0]}},
        "11": {"class_type": "SaveWEBM", "inputs": {"images": ["10", 0], "filename_prefix": "char9000_wan", "codec": "vp9", "fps": 16.0, "crf": 32.0}},
    }


def wan13b(prompt="a worker in high-visibility PPE walking through a clean modern plant, cinematic", seed=1,
           width=832, height=480, length=33):
    # RTX 4090 default: Wan2.1 T2V 1.3B (~8 GB VRAM) at 20 steps; no CausVid LoRA (that LoRA is for 14B)
    wf = wan(prompt, seed, unet="wan2.1_t2v_1.3B_fp16.safetensors", width=width, height=height, length=length)
    del wf["2"]
    wf["3"]["inputs"]["model"] = ["1", 0]
    wf["9"]["inputs"].update({"steps": 20, "cfg": 6.0})
    return wf


# wan14b needs ComfyUI weight offload on 24 GB (--lowvram); it is kept for parity but not in the default test set.
WORKFLOWS = {"sdxl": sdxl, "flux": flux, "ltxv": ltxv, "wan13b": wan13b, "wan14b": wan}


def _req(path, data=None):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def run(name, timeout=1800):
    pid = _req("/prompt", {"prompt": WORKFLOWS[name]()})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = _req(f"/history/{pid}").get(pid)
        if h and h.get("status", {}).get("completed") is not None:
            st = h["status"]
            files = [f["filename"] for o in h.get("outputs", {}).values() for k in ("images", "gifs", "videos") for f in o.get(k, [])]
            err = [m for m in st.get("messages", []) if m[0] == "execution_error"]
            return st.get("status_str"), round(time.time() - t0, 1), files, (err[0][1].get("exception_message") if err else None)
        time.sleep(2)
    return "timeout", timeout, [], None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "export":
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        for n, fn in WORKFLOWS.items():
            json.dump(fn(), open(os.path.join(out, f"{n}.api.json"), "w"), indent=2)
        print("exported", list(WORKFLOWS), "to", out)
    else:
        for n in sys.argv[2:] or [k for k in WORKFLOWS if k != "wan14b"]:
            print(n, *run(n), flush=True)
