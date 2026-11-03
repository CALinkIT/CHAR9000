# CHAR9000 Guide

Hi! This is how to use CHAR9000 and get the most out of it. Everything here runs on your PC.

Installing? See `docs/CHAR9000-Installation.md` first.

## 0. Getting started (5 minutes)

1. Double-click **CHAR9000** on the desktop (opens http://localhost:3000) and sign in.
2. Check the model menu at the top says **CHAR9000:latest**.
3. Type: *"Hi! Friend mode. What can you help me with?"*
4. Try one thing from each mode in §2.
5. Drop a few of your own notes into `C:\CHAR9000\data\files` and run `.\scripts\char9000.ps1 ingest` (§3).

Tip: CHAR9000 starts in about 10-30 seconds after the PC wakes, because the model has to load onto the GPU.
The first answer is slower; after that it's fast.

## 1. The pieces

| You use | What it is | Where |
|---|---|---|
| **Chat** | Open WebUI — the chat window | http://localhost:3000 |
| **Models** | The "brains", run by Ollama on your GPU | picked in the chat's model menu |
| **My Documents** | CHAR9000's memory of your files (knowledge base) | `data\files` folder |
| **Automations** | n8n — visual workflows (reminders, routines, mini-apps) | http://localhost:5678 |
| **Crew** | A team of AI agents (planner, researcher, build partner, executor) | model `crewai` in chat, or the API |
| **Smart tools** | Pydantic AI — summarize, classify, extract into clean JSON | http://localhost:8001/docs |
| **Images** | ComfyUI (optional) — makes pictures and short videos | http://localhost:8188 |

## 2. Talking to CHAR9000

Pick **CHAR9000:latest** in the model menu. It has four modes — just say which one:

### Friend mode
- "Hey CHAR9000, friend mode. I had a weird day — can I tell you about it?"
- "Give me three fun things to do this weekend that cost under $20."
- "Remember when I asked Dad to build you? What do you want to be when *you* grow up?"

### Plan mode
- "Plan mode: I have a chem test Friday, a project due Monday and work Saturday. Make me a schedule."
- "Help me build a monthly budget. I earn about $___ and spend on ___."
- "I want to get better at running. Make a 6-week plan starting from zero."
- "Turn this brain-dump into a to-do list with priorities: ..."

### Build mode
- "Build mode: help me make a Python script that renames my photos by date taken."
- "I want to make an LED that changes color with the weather using an ESP32. Where do I start?"
- "My PC is slow when gaming. Walk me through checking temps and what's using the GPU."
- Switch to **qwen2.5-coder:14b** for longer coding sessions.

### Teach me
- "Teach me what a token is, then show me how to count tokens in a sentence."
- "How do you actually work? Explain like I'm smart but new to AI."
- "What's the difference between you and ChatGPT?" (You run locally; it runs in a datacenter.)
- "Teach me what embeddings are with an experiment I can run." (See §6.)
- Pick **deepseek-r1:8b** to *see* a model's step-by-step reasoning.

### More things to try
- Drop a photo into chat with **llama3.2-vision**: "What plant is this and how do I keep it alive?"
- Turn on **Image** in the chat bar (needs ComfyUI): "A cozy pixel-art bedroom with a cat on a gaming chair."
- Compare models: ask the same question to CHAR9000, gpt-oss:20b and gemma3. Which is best? Why?

## 3. Giving CHAR9000 your documents

1. Copy notes, PDFs, Word docs, `.txt` or `.md` files into `data\files`.
2. Run `.\scripts\char9000.ps1 ingest`.
3. Ask the crew or chat: "Using my documents, what did my biology notes say about mitosis?"

You can also make knowledge bases right in the chat: **Workspace → Knowledge → +**, upload files,
then type `#` in a chat to attach one.

## 4. The crew (multi-agent)

Pick model **crewai** in chat, or from PowerShell:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/crew/kickoff -ContentType application/json `
  -Body '{"message":"Plan a gaming PC upgrade under $600 and explain each choice."}'
```

Other ideas: "Research and plan a 3-day road trip", "Design a beginner Arduino project and write its code".
It is slower (a few minutes) because four agents take turns.

## 5. Smart tools (clean JSON out)

```powershell
$h = @{ "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post http://localhost:8001/summarize -Headers $h `
  -Body '{"text":"(paste an article here)","max_length":80}'
Invoke-RestMethod -Method Post http://localhost:8001/extract -Headers $h `
  -Body '{"text":"Dentist appointment with Dr. Lee on March 3 at 4pm, bring insurance card.","fields":["who","date","time","notes"]}'
```

Open http://localhost:8001/docs to try them in the browser.

## 6. Learn AI by doing (mini-labs)

| Lab | Try |
|---|---|
| Tokens & speed | `ollama run qwen3.6:27b --verbose "Write a haiku about GPUs"` — look at "eval rate" (tokens/second) |
| Temperature | Ask CHAR9000 for a story twice. Then in chat settings set temperature 0 and ask again. What changed? |
| System prompts | Open `identity\core_prompt.md`. That's CHAR9000's "personality instructions". Make a copy, change the tone, build a test model: `ollama create test-me -f mymodelfile` |
| Embeddings | `Invoke-RestMethod -Method Post http://localhost:11434/api/embed -Body '{"model":"nomic-embed-text","input":"cat"}'` — that list of 768 numbers is what "meaning" looks like to an AI. Compare "cat", "kitten", "car". |
| RAG | Ingest one file, ask about it with and without the knowledge base. Notice the difference. |
| Agents | Build an n8n workflow: Webhook → AI Agent (Ollama, gpt-oss:20b) → Respond. Call it with `Invoke-RestMethod`. |
| GPU memory | `nvidia-smi` while chatting, then while generating an image. Why can't both be huge at once? |
| Hallucinations | Ask about a made-up book. Does it admit it doesn't know? (It should!) |

## 7. Automations with n8n

Open http://localhost:5678, create your owner account, then try:
1. **Morning briefing:** Schedule (7am) → AI Agent ("motivational quote + today's 3 priorities") → save to `/data/shared/briefing.md`.
2. **Ask-me webhook:** Webhook → Basic LLM Chain (CHAR9000) → Respond to Webhook.
3. **Homework helper:** Webhook → Qdrant search (my_documents) → LLM → Respond.

CHAR9000 always asks before running an automation that changes things (charter §3).

## 8. Agency levels

CHAR9000 starts at **Level 1 (Helper)**: it chats, plans, explains and drafts, but asks before doing
anything that changes something. When you want it to do more on its own, change
`identity\autonomy.yaml` (see `identity\charter.md`). Every action it takes is logged — see what it did:

```powershell
docker exec char9000-postgres psql -U char9000 -d n8n -c "SELECT logged_at, action, target, result FROM char9000_audit.audit_log ORDER BY id DESC LIMIT 10;"
```

## 9. Images (optional ComfyUI)

1. Download **ComfyUI portable for Windows (NVIDIA)** from the ComfyUI GitHub releases and unzip to `C:\ComfyUI`.
2. Put `flux1-schnell-fp8.safetensors` in `ComfyUI\models\checkpoints\FLUX\`. Only use `.safetensors` files.
3. Start it with `run_nvidia_gpu.bat` (add `--reserve-vram 2` to the command line in that file).
4. Connect chat to it: `$env:OWUI_EMAIL="you@..."; $env:OWUI_PASSWORD="..."; python scripts\owui_enable_comfyui.py`
5. Before big image or video jobs: `.\scripts\char9000.ps1 free-gpu`.

## 10. Using the chat app

| Feature | How |
|---|---|
| New chat / history | left sidebar; chats are saved on this PC |
| Folders & tags | drag chats into folders; right-click to tag or pin |
| Search old chats | sidebar search box |
| Switch model mid-chat | model menu at the top; each answer shows which model wrote it |
| Compare two models | **+** next to the model menu → pick a second model → both answer side by side |
| Regenerate / edit | hover a message → regenerate, or edit your question and resend |
| Attach files | paperclip → PDF, Word, text, images (images need llama3.2-vision) |
| Voice | microphone button (speech-to-text runs locally); speaker icon reads answers aloud |
| Memory | Settings → Personalization → Memory: tell it facts to remember ("my cat is named Pixel"). You can see and delete every memory there |
| Export | chat menu (⋯) → Download (Markdown, PDF or JSON) |
| Archive / delete | chat menu (⋯) → Archive or Delete |
| Dark mode, language | Settings → General |

## 11. Customizing the personality

CHAR9000's personality lives in plain text files you can edit:

- `identity\personality.md` — who CHAR9000 is (traits, voice, modes, boundaries). Edit this first.
- `identity\core_prompt.md` — the system prompt the model actually gets.

After editing `core_prompt.md`, rebuild the model:
```powershell
.\scripts\install.ps1 -OwnerName "<your name>" -SkipModels
```
Or, without rebuilding: Admin Panel → Settings → Models → CHAR9000:latest → System Prompt → paste the new text.

Ideas: change its nickname for you, add your interests ("loves astronomy and Minecraft"), set a
humor level, add a new mode ("study buddy mode: quiz me with flashcards"). Keep the safety and
honesty rules; they're there to protect you.

You can also make extra characters: Workspace → Models → **+** → base model `qwen3.6:27b`, give it a
name, avatar and system prompt (e.g. a strict coding mentor, a Spanish tutor, a D&D game master).

## 12. Privacy

- Everything (models, chats, memories, documents) is stored on this PC. No online AI service is used.
- Only this computer can open CHAR9000 (it listens on `localhost` only).
- Passwords and keys were generated just for this PC and are in `C:\CHAR9000\.env`. Don't share that file or the `data\backups` folder.
- Delete anything any time: chats (chat menu → Delete), memories (Settings → Personalization), documents (remove from `data\files` and re-ingest).
- The internet is needed only for installing, updating and downloading models.

## 13. Everyday tips

- **Gaming?** Run `.\scripts\char9000.ps1 free-gpu` first so games get all 24 GB of the GPU. CHAR9000 reloads when you chat again.
- **Short on time?** Use **gpt-oss:20b** for quick answers; **CHAR9000** for the personality; **deepseek-r1:8b** to watch it think.
- **Long documents:** ask for a summary first, then ask follow-up questions.
- **Check its work:** CHAR9000 can be wrong. For anything important (health, money, safety, homework facts), double-check with a trusted source.
- **Weekly:** `.\scripts\char9000.ps1 backup`, and copy the newest `data\backups` folder to an external drive.

## 14. When something's wrong

| Problem | Fix |
|---|---|
| Chat page won't load | Is Docker Desktop running? `.\scripts\char9000.ps1 start` |
| "Model not found" / no models listed | Start Ollama (Start menu → Ollama); `.\scripts\char9000.ps1 status` |
| Very slow answers | Something else is using the GPU (a game?) — `free-gpu`, or pick a smaller model |
| Image generation out of memory | `free-gpu` first; use FLUX schnell, not big video models |
| Everything broken after an update | `.\scripts\char9000.ps1 restart`; still broken → ask Dad (or CHAR9000 in build mode!) |

**Never** run `docker compose down -v` unless you mean to erase CHAR9000's memory and chats.
