# CxBolt Voice Bot

An AI-powered voice agent that conducts insurance qualification calls. Sarah — the AI agent — calls prospects, follows a structured qualification script, and hands off qualified leads to a human specialist.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Breakdown](#component-breakdown)
- [Data Flow](#data-flow)
- [Two Modes](#two-modes)
- [Tech Stack](#tech-stack)
- [File Structure](#file-structure)
- [Current Limitations](#current-limitations)
- [Planned Improvements](#planned-improvements)
- [Quick Start](#quick-start)

---

## Overview

CxBolt is a voice bot pipeline that combines three AI models running locally:

1. **STT** — Converts caller speech to text (Faster-Whisper)
2. **LLM** — Processes the text and generates a response (Llama 3 via Ollama)
3. **TTS** — Converts the response back to natural speech (Kokoro ONNX)

The bot follows a fixed qualification script — it cannot deviate from it. When a lead qualifies, it hands off to a human specialist.

---

## System Architecture

### Demo Mode (Local — No Cloud)

```
┌─────────────────────────────────────────────────────────┐
│                      MacBook (Local)                     │
│                                                         │
│   Microphone                                            │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────┐    audio     ┌──────────────────┐     │
│  │  sounddevice │ ──────────► │  Faster-Whisper  │     │
│  │  (recording) │             │  (STT — base.en) │     │
│  └─────────────┘             └────────┬─────────┘     │
│                                        │ text           │
│                                        ▼               │
│                               ┌─────────────────┐      │
│                               │  Ollama (LLM)   │      │
│                               │  llama3:latest  │      │
│                               │  localhost:11434│      │
│                               └────────┬────────┘      │
│                                        │ text           │
│                                        ▼               │
│                               ┌─────────────────┐      │
│                               │  Kokoro ONNX    │      │
│                               │  (TTS — Sarah)  │      │
│                               │  af_sarah voice │      │
│                               └────────┬────────┘      │
│                                        │ audio          │
│                                        ▼               │
│                                   Speaker/Output        │
└─────────────────────────────────────────────────────────┘
```

### Production Mode (Real Phone Calls)

```
                         Inbound Call
                              │
                              ▼
                    ┌─────────────────┐
                    │     Twilio      │
                    │  (Phone Number) │
                    └────────┬────────┘
                             │ SIP/WebRTC
                             ▼
                    ┌─────────────────┐
                    │    LiveKit      │
                    │  (Real-time     │
                    │   Media Server) │
                    └────────┬────────┘
                             │ audio stream
                             ▼
┌────────────────────────────────────────────────┐
│                MacBook / Server                 │
│                                                │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐  │
│  │ Whisper  │   │  Llama 3 │   │  TTS      │  │
│  │  (STT)   │──►│  (LLM)   │──►│ (Kokoro / │  │
│  │          │   │  Ollama  │   │  OpenAI)  │  │
│  └──────────┘   └──────────┘   └───────────┘  │
│                                                │
│        LiveKit Agents Framework (agent.py)     │
└────────────────────────────────────────────────┘
                             │ audio stream
                             ▼
                    ┌─────────────────┐
                    │    LiveKit      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Twilio      │
                    └────────┬────────┘
                             │
                             ▼
                        Caller's Phone
```

---

## Component Breakdown

### 1. Speech-to-Text (STT) — Faster-Whisper
- **Model:** `base.en` (~145 MB)
- **Library:** `faster-whisper` — optimised port of OpenAI Whisper using CTranslate2
- **Runs:** Fully local on CPU, no API key needed
- **Latency:** ~1–2 seconds per utterance on MacBook
- **Cost:** $0

### 2. Language Model (LLM) — Ollama + Llama 3
- **Model:** `llama3:latest` (4.7 GB, runs locally)
- **Server:** Ollama at `http://localhost:11434`
- **Interface:** OpenAI-compatible REST API (`/api/chat`)
- **Config:** temperature 0.3, max 150 tokens (keeps responses short for phone calls)
- **Cost:** $0

### 3. Text-to-Speech (TTS) — Kokoro ONNX
- **Model:** `kokoro-v1.0.int8.onnx` (88 MB) with `voices-v1.0.bin` (27 MB)
- **Voice:** `af_sarah` — American female, neural voice
- **Sample rate:** 24,000 Hz
- **Library:** `kokoro-onnx` using ONNX Runtime
- **Latency:** ~0.5–1 second to generate
- **Cost:** $0

### 4. Audio I/O — sounddevice
- **Recording:** 16,000 Hz, mono, float32, 6-second windows
- **Playback:** Direct to system audio at 24,000 Hz
- **Library:** `sounddevice` (PortAudio bindings)

### 5. Qualification Script (Business Logic)
Hardcoded in the system prompt. Five binary questions:

| # | Question | Pass Condition |
|---|----------|---------------|
| Q1 | Age 19–64? | YES |
| Q2 | Income below $30,000/year? | YES |
| Q3 | U.S. citizen or permanent resident? | YES |
| Q4 | Has Medicare/Medicaid/employer insurance? | NO |
| Q5 | Enrolled in marketplace plan in last 60 days? | NO |

All five must pass → transfer to specialist. Any fail → polite end of call.

### 6. LiveKit Agents (Production Only)
- **Framework:** `livekit-agents` — handles real-time audio streaming, VAD, and the STT→LLM→TTS pipeline
- **VAD:** Silero VAD (`livekit-plugins-silero`) — detects when the caller starts/stops speaking
- **Noise cancellation:** Built into `RoomInputOptions`
- **Concurrency:** Each inbound call gets its own isolated agent session

---

## Data Flow

### Demo Mode (Voice)
```
1. sounddevice records 6s of audio from mic
2. Audio saved to temp .wav file
3. Faster-Whisper transcribes to text
4. Text appended to conversation history
5. Full conversation sent to Ollama LLM
6. LLM returns Sarah's next response (max 150 tokens)
7. Kokoro ONNX synthesises speech from text
8. sounddevice plays audio to speaker
9. Loop back to step 1
10. Call ends when qualification outcome phrase detected
```

### Production Mode
```
1. Twilio receives inbound call on phone number
2. Twilio routes audio to LiveKit via SIP
3. LiveKit streams audio to agent.py running on server
4. Silero VAD detects end of caller's speech
5. Whisper STT transcribes the audio segment
6. Text sent to Ollama LLM with full conversation context
7. LLM response sent to TTS
8. TTS audio streamed back through LiveKit → Twilio → caller's phone
9. Loop continues until call ends
```

---

## Two Modes

| Feature | Demo Mode (`demo_standalone.py`) | Production Mode (`agent.py`) |
|---------|----------------------------------|------------------------------|
| Phone number | No | Yes (via Twilio) |
| Real calls | No | Yes |
| Internet required | No | Yes (LiveKit, Twilio) |
| Latency | ~3–5s/turn | ~2–4s/turn |
| Concurrency | 1 call | Multiple simultaneous |
| VAD | No (fixed 6s windows) | Yes (Silero VAD) |
| Noise cancellation | No | Yes |
| Cost | $0 | Twilio + LiveKit fees |

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| LLM runtime | Ollama | Latest |
| LLM model | Llama 3 | 8B |
| STT | Faster-Whisper | 1.x |
| TTS | Kokoro ONNX | 0.4.x |
| Audio I/O | sounddevice + PortAudio | 0.5.x |
| Inference engine | ONNX Runtime | 1.x |
| Async HTTP | aiohttp | 3.x |
| Production framework | LiveKit Agents | 0.12+ |
| Telephony | Twilio | — |

---

## File Structure

```
cxbolt-voicebot/
├── demo_standalone.py     # Local demo — text or voice, no LiveKit needed
├── agent.py               # Production agent — LiveKit + Twilio
├── requirements.txt       # All Python dependencies
├── SETUP_GUIDE.md         # Step-by-step setup instructions
├── .gitignore             # Excludes .env, venv, model files
├── .env                   # Your credentials (never committed)
│
├── kokoro-v1.0.int8.onnx  # Kokoro TTS model (88MB, not in git)
├── voices-v1.0.bin        # Kokoro voice embeddings (27MB, not in git)
└── silero_vad.onnx        # Silero VAD model (2.2MB, not in git)
```

> Model files are excluded from git. Download with:
> ```bash
> # Kokoro TTS
> curl -L -o kokoro-v1.0.int8.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
> curl -L -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
> # Silero VAD
> curl -L -o silero_vad.onnx https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx
> ```

---

## Current Limitations

1. **Fixed recording windows** — Demo mode records in 6-second chunks regardless of when the caller finishes speaking. No VAD in demo mode.
2. **Single concurrent call** — Demo mode handles one conversation at a time.
3. **No call logging** — Conversations are not saved or logged anywhere.
4. **No CRM integration** — Qualified leads are not automatically pushed to any CRM.
5. **No interruption handling** — If the caller speaks over Sarah, it is not handled gracefully.
6. **Local only** — LLM and STT run on the same machine as the bot. No GPU acceleration.
7. **English only** — Whisper is configured for English (`base.en`).
8. **No call transfer** — When a lead qualifies, Sarah announces the transfer but there is no actual warm transfer mechanism yet.

---

## Planned Improvements

| Priority | Improvement | Impact |
|----------|------------|--------|
| High | Add VAD to demo mode (Silero) | Natural turn-taking, no fixed 6s windows |
| High | Real call transfer on qualification | Full end-to-end lead handling |
| High | Call logging + transcript storage | Compliance, QA, analytics |
| Medium | CRM integration (HubSpot / Salesforce) | Auto-push qualified leads |
| Medium | ElevenLabs TTS option | Even more natural voice |
| Medium | GPU acceleration for Whisper | Reduce STT latency to <0.5s |
| Medium | Multi-language support | Spanish-speaking prospects |
| Low | Dashboard / monitoring | Live call monitoring, metrics |
| Low | A/B test different scripts | Optimise qualification rate |
| Low | Sentiment detection | Flag frustrated callers for human takeover |

---

## Quick Start

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for full instructions.

**TL;DR:**
```bash
# 1. Start Ollama
ollama serve

# 2. Run demo
cd ~/Desktop/cxbolt-voicebot
source .venv/bin/activate
python demo_standalone.py
# Choose 1 (text) or 2 (voice)
```

---

*Built by CxBolt — Bilal & Umair*
