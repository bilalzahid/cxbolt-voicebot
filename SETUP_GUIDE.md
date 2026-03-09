# CxBolt Voice Bot — Complete Setup Guide (MacBook)

> **3 Phases:** Start with Phase 1 (text demo, 15 mins). Move to Phase 2 (voice on your Mac). Then Phase 3 (real phone calls via Twilio).

---

## Prerequisites — Do These First

### 1. Install Homebrew (if not already installed)
Open Terminal and run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python 3.11+
```bash
brew install python@3.11
python3 --version   # should show 3.11.x or higher
```

### 3. Install Git (if not already)
```bash
brew install git
git --version
```

---

## GitHub Setup

### 1. Create the Repository
1. Go to [github.com](https://github.com) → Sign in
2. Click **"New"** (green button, top left)
3. Repository name: `cxbolt-voicebot`
4. Set to **Private**
5. Do NOT add README or .gitignore (you already have them)
6. Click **"Create repository"**

### 2. Push Your Code
In Terminal, navigate to wherever you saved the project folder:
```bash
cd ~/Desktop/cxbolt-voicebot   # adjust path as needed

git init
git add .
git commit -m "Initial commit — CxBolt voice bot"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/cxbolt-voicebot.git
git push -u origin main
```

> Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.

---

## Phase 1 — Text Demo (No Hardware, No Accounts Needed)

**Time to complete: ~15 minutes**

### Step 1: Install Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Or download the Mac installer from [ollama.com](https://ollama.com) — just drag to Applications.

### Step 2: Pull the AI Model
```bash
ollama pull llama3.1:8b
```

> This downloads ~4.7GB. Do this on WiFi. Takes 5–15 minutes depending on connection.

### Step 3: Start Ollama
Open a **new Terminal window** and run:
```bash
ollama serve
```

> Leave this terminal open — Ollama must stay running.

### Step 4: Install Python Dependencies
Open **another Terminal window** (keep the Ollama one running):
```bash
cd ~/Desktop/cxbolt-voicebot   # navigate to your project folder
pip3 install aiohttp python-dotenv
```

### Step 5: Run the Text Demo
```bash
python3 demo_standalone.py
```

Choose **option 1** (Text mode). You'll see Sarah's opening message. Type your responses and test the full qualification flow.

**Expected output:**
```
🤖 Sarah: Hello! This is Sarah calling from Insurance Solutions...
👤 You: yes
🤖 Sarah: Great! To check if you qualify, I just need a few quick questions...
```

---

## Phase 2 — Voice Demo (Speak & Listen on Your Mac)

**Time to complete: ~10 minutes after Phase 1**

> Your Mac has a built-in microphone and speaker, so no extra hardware needed.

### Step 1: Install Voice Dependencies
```bash
pip3 install faster-whisper sounddevice numpy soundfile
```

### Step 2: Allow Microphone Access
When you first run voice mode, macOS will ask for microphone permission. Click **Allow**.

### Step 3: Run Voice Demo
```bash
python3 demo_standalone.py
```

Choose **option 2** (Voice mode). Wait for Whisper to load (~30 seconds first time), then speak when prompted.

> **Note:** The voice output uses your Mac's built-in `say` command with the Samantha voice — no extra setup needed.

---

## Phase 3 — Real Phone Calls (Twilio + LiveKit)

**Time to complete: ~45–60 minutes**

This connects the bot to an actual phone number that people can call.

---

### Part A: Twilio Setup

#### 1. Create a Twilio Account
1. Go to [twilio.com](https://twilio.com) → Click **"Sign up for free"**
2. Verify your email and phone number
3. Answer "What are you building?" → select **Voice** and **Python**

#### 2. Get Your Credentials
From the [Twilio Console dashboard](https://console.twilio.com):
- Copy your **Account SID** (starts with `AC...`)
- Copy your **Auth Token** (click the eye icon to reveal)

#### 3. Get a Twilio Phone Number
1. In Twilio Console → **Phone Numbers** → **Manage** → **Buy a number**
2. Select **Voice** capability
3. Pick any US number → Click **Buy**
4. Free trial gives you $15 credit — plenty for testing

---

### Part B: LiveKit Setup

#### 1. Create a LiveKit Cloud Account
1. Go to [cloud.livekit.io](https://cloud.livekit.io) → Sign up (free)
2. Create a new **Project**
3. Go to **Settings** → **Keys** → **Create API Key**
4. Copy the **API Key** and **API Secret** (only shown once!)
5. Also copy your **WebSocket URL** (looks like `wss://your-project.livekit.cloud`)

#### 2. Connect Twilio to LiveKit
1. In LiveKit dashboard → **SIP** → **Configure Twilio integration**
2. Follow the guide — it gives you a webhook URL to paste into Twilio
3. In Twilio Console → Your phone number → **Voice** section → paste the LiveKit webhook URL as the **"A call comes in"** webhook

---

### Part C: ngrok Setup (Exposes Your Mac to the Internet)

#### 1. Install ngrok
```bash
brew install ngrok
```

#### 2. Create Free Account
Go to [ngrok.com](https://ngrok.com) → Sign up → Copy your **authtoken** from the dashboard.

#### 3. Authenticate ngrok
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

#### 4. Start ngrok (when running the agent)
```bash
ngrok http 8080
```

Copy the `https://xxxx.ngrok.io` URL — you'll use this in webhook configurations.

---

### Part D: Configure and Run the Agent

#### 1. Create Your .env File
```bash
cd ~/Desktop/cxbolt-voicebot
cp .env.example .env
```

Open `.env` in TextEdit or any editor and fill in:
```
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here

TWILIO_ACCOUNT_SID=ACxxxxxxx
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

#### 2. Install All Dependencies
```bash
pip3 install -r requirements.txt
```

#### 3. Run Everything (3 Terminals)

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — ngrok:**
```bash
ngrok http 8080
```

**Terminal 3 — LiveKit Agent:**
```bash
python3 agent.py start
```

#### 4. Test It
Call your Twilio phone number from any phone. Sarah should answer within 2–3 seconds.

---

## Troubleshooting

### "Cannot connect to Ollama"
Make sure `ollama serve` is running in a separate terminal. Check with:
```bash
curl http://localhost:11434/api/tags
```

### "No module named 'aiohttp'"
```bash
pip3 install aiohttp
```

### Whisper model download is slow
The `base.en` model is ~150MB. Run `demo_standalone.py` once and let it download fully.

### Twilio call connects but no voice
Check that your LiveKit webhook URL in Twilio is correct and ngrok is running.

### Ollama is too slow / responses take >5 seconds
Try a smaller model:
```bash
ollama pull phi3:mini
```
Then change `llama3.1:8b` to `phi3:mini` in `demo_standalone.py` line 67.

---

## Quick Reference

| What | Command |
|------|---------|
| Start Ollama | `ollama serve` |
| Text demo | `python3 demo_standalone.py` → choose 1 |
| Voice demo | `python3 demo_standalone.py` → choose 2 |
| Full agent | `python3 agent.py start` |
| Check Ollama models | `ollama list` |
| Pull better model | `ollama pull llama3.1:8b` |

---

## What Each File Does

| File | Purpose |
|------|---------|
| `demo_standalone.py` | Run the bot locally — text or voice, no LiveKit needed |
| `agent.py` | Full production agent — connects to LiveKit + Twilio |
| `requirements.txt` | All Python packages needed |
| `.env.example` | Template for your credentials (copy to `.env`) |
| `.gitignore` | Keeps secrets out of GitHub |

---

*Built by CxBolt — Bilal & Umair*
