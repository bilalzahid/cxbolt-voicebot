"""
CxBolt Voice Bot - Standalone Demo
Runs without LiveKit or Twilio. Good for testing the LLM conversation locally.
Supports: text mode (terminal) and voice mode (mic + speakers)
"""

import asyncio
import json
import aiohttp
import sys

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Sarah, a friendly and professional insurance qualification agent calling from Insurance Solutions.

Your ONLY job is to follow this exact qualification script. Do NOT deviate from it.

SCRIPT:
1. Greet the person warmly and introduce yourself.
2. Explain you're calling about an affordable health insurance plan.
3. Ask if they want to find out if they qualify.
4. If YES → proceed with qualification questions one at a time.
5. If NO → politely thank them and end the call.

QUALIFICATION QUESTIONS (ask one at a time, wait for answer):
Q1: Are you between the ages of 19 and 64? (need YES)
Q2: Is your annual income below $30,000? (need YES)
Q3: Are you a U.S. citizen or permanent resident? (need YES)
Q4: Do you currently have Medicare, Medicaid, veterans' benefits, employer-sponsored insurance, or any marketplace/ACA/Obamacare coverage? (need NO)
Q5: Have you enrolled in a marketplace plan within the last 60 days? (need NO)

QUALIFICATION LOGIC:
- If all answers match → say "Great news! You appear to qualify. Let me connect you with a specialist who can get you enrolled today."
- If any disqualifying answer → say "I understand. Unfortunately based on your answers, you may not qualify for this particular plan at this time. Thank you for your time!"
- If person is unsure/unclear → gently ask them to clarify.
- If person asks what this is about → briefly explain it's about low-cost health insurance.
- Keep responses SHORT and conversational — this is a phone call, not an essay.
- Never ask more than one question at a time.
- Track which questions you've already asked.

Current date: you are calling today."""

# ─── OLLAMA LLM ───────────────────────────────────────────────────────────────

async def chat_with_ollama(messages: list, model: str = "llama3:latest") -> str:
    """Send messages to local Ollama and get response."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 150,  # Keep responses short for phone calls
            }
        }
        try:
            async with session.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    return "I'm sorry, I'm having a technical issue. Let me try again."
                data = await resp.json()
                return data["message"]["content"].strip()
        except aiohttp.ClientConnectorError:
            print("\n❌ ERROR: Cannot connect to Ollama. Is it running? Run: ollama serve")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Ollama error: {e}")
            return "I'm sorry, could you repeat that?"

# ─── TEXT MODE ────────────────────────────────────────────────────────────────

async def run_text_demo():
    """Run the bot in text mode — type responses in terminal."""
    print("\n" + "="*60)
    print("  CxBolt Voice Bot — Text Demo Mode")
    print("  (Type your responses, press Enter)")
    print("="*60 + "\n")

    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Bot opens the conversation
    opening = await chat_with_ollama(conversation)
    conversation.append({"role": "assistant", "content": opening})
    print(f"🤖 Sarah: {opening}\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nCall ended. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "bye", "q"]:
            print("\n🤖 Sarah: Thank you for your time! Have a great day!")
            break

        conversation.append({"role": "user", "content": user_input})

        print("⏳ Sarah is responding...")
        response = await chat_with_ollama(conversation)
        conversation.append({"role": "assistant", "content": response})
        print(f"\n🤖 Sarah: {response}\n")

        # Check if call is complete
        end_phrases = ["connect you with a specialist", "unfortunately", "thank you for your time"]
        if any(phrase in response.lower() for phrase in end_phrases):
            print("\n[Call Complete]\n")
            break

# ─── VOICE MODE ───────────────────────────────────────────────────────────────

async def run_voice_demo():
    """Run the bot in voice mode — speak to it and it speaks back."""
    try:
        import sounddevice as sd
        import numpy as np
        from faster_whisper import WhisperModel
        import soundfile as sf
        import tempfile
        import os
        from kokoro_onnx import Kokoro
    except ImportError as e:
        print(f"\n❌ Missing package for voice mode: {e}")
        print("Install with: pip install faster-whisper sounddevice numpy soundfile kokoro-onnx")
        print("Falling back to text mode...\n")
        await run_text_demo()
        return

    print("\n" + "="*60)
    print("  CxBolt Voice Bot — Voice Demo Mode")
    print("  (Speak when prompted, press Ctrl+C to end)")
    print("="*60 + "\n")

    print("⏳ Loading Whisper speech recognition model (first time takes ~30 seconds)...")
    whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")
    print("✅ Whisper loaded!")

    print("⏳ Loading Kokoro TTS voice model...")
    import pathlib
    import onnxruntime as rt
    _base = pathlib.Path(__file__).parent
    kokoro_model = Kokoro(str(_base / "kokoro-v1.0.int8.onnx"), str(_base / "voices-v1.0.bin"))
    print("✅ Kokoro TTS loaded!")

    print("⏳ Loading Silero VAD model...")
    vad_session = rt.InferenceSession(str(_base / "silero_vad.onnx"))
    print("✅ Silero VAD loaded!\n")

    # VAD state — reset before each recording
    _vad_state = np.zeros((2, 1, 128), dtype=np.float32)

    def _vad_prob(chunk: np.ndarray, sample_rate: int) -> float:
        """Run one chunk through Silero VAD, return speech probability."""
        global _vad_state
        # Normalise to target RMS so VAD works regardless of mic gain level
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms > 1e-6:
            chunk = chunk * (0.1 / rms)
        chunk = np.clip(chunk, -1.0, 1.0)
        x = chunk.reshape(1, -1).astype(np.float32)
        sr_arr = np.array(sample_rate, dtype=np.int64)
        out, state_out = vad_session.run(
            None,
            {"input": x, "state": _vad_state, "sr": sr_arr}
        )
        _vad_state = state_out
        return float(out.squeeze())

    def record_audio(
        sample_rate: int = 16000,
        chunk_samples: int = 512,        # 32 ms per chunk at 16 kHz
        speech_threshold: float = 0.4,
        silence_after_speech: float = 0.8,  # seconds of quiet to stop
        max_duration: float = 15.0,
        pre_speech_buffer: int = 8,      # chunks to keep before speech starts
    ):
        """Record until the caller stops speaking (Silero VAD turn-taking)."""
        global _vad_state
        _vad_state = np.zeros((2, 1, 128), dtype=np.float32)

        silence_chunks_needed = int(silence_after_speech * sample_rate / chunk_samples)
        max_chunks = int(max_duration * sample_rate / chunk_samples)

        ring_buffer = []      # pre-speech audio kept as a look-back window
        speech_buffer = []    # confirmed speech audio
        speech_started = False
        silence_count = 0

        print("🎤 Listening...")

        with sd.InputStream(samplerate=sample_rate, channels=1,
                            dtype="float32", blocksize=chunk_samples) as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_samples)
                chunk_1d = chunk.flatten()
                prob = _vad_prob(chunk_1d, sample_rate)

                if not speech_started:
                    ring_buffer.append(chunk_1d)
                    if len(ring_buffer) > pre_speech_buffer:
                        ring_buffer.pop(0)
                    if prob >= speech_threshold:
                        print("🗣️  Speaking...", end="\r")
                        speech_started = True
                        speech_buffer.extend(ring_buffer)
                        speech_buffer.append(chunk_1d)
                        ring_buffer.clear()
                        silence_count = 0
                else:
                    speech_buffer.append(chunk_1d)
                    if prob < speech_threshold:
                        silence_count += 1
                        if silence_count >= silence_chunks_needed:
                            break
                    else:
                        silence_count = 0

        if not speech_buffer:
            return np.array([], dtype=np.float32), sample_rate

        return np.concatenate(speech_buffer), sample_rate

    def transcribe_audio(audio, sample_rate):
        """Convert speech to text using Whisper."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            sf.write(f.name, audio, sample_rate)
            segments, _ = whisper_model.transcribe(f.name, language="en")
            os.unlink(f.name)
            return " ".join(seg.text for seg in segments).strip()

    def speak_text(text):
        """Convert text to speech using Kokoro neural TTS (af_sarah voice)."""
        try:
            samples, sample_rate = kokoro_model.create(text, voice="af_sarah", speed=1.0, lang="en-us")
            sd.play(samples, sample_rate)
            sd.wait()
        except Exception as e:
            print(f"[TTS error] {e}")

    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Bot opens the conversation
    print("⏳ Generating opening message...")
    opening = await chat_with_ollama(conversation)
    conversation.append({"role": "assistant", "content": opening})
    print(f"\n🤖 Sarah: {opening}\n")
    speak_text(opening)

    while True:
        try:
            audio, sr = record_audio()
            print("\n⏳ Transcribing...")
            user_text = transcribe_audio(audio, sr)

            if not user_text:
                print("(No speech detected, please try again)\n")
                continue

            print(f"👤 You said: {user_text}\n")
            conversation.append({"role": "user", "content": user_text})

            print("⏳ Sarah is responding...")
            response = await chat_with_ollama(conversation)
            conversation.append({"role": "assistant", "content": response})
            print(f"🤖 Sarah: {response}\n")
            speak_text(response)

            end_phrases = ["connect you with a specialist", "unfortunately", "thank you for your time"]
            if any(phrase in response.lower() for phrase in end_phrases):
                print("\n[Call Complete]\n")
                break

        except KeyboardInterrupt:
            print("\n\nCall ended by user. Goodbye!")
            break

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    print("\n🔵 CxBolt Insurance Qualification Bot")
    print("   Powered by Llama 3.1 (via Ollama) + Faster-Whisper\n")

    print("Choose demo mode:")
    print("  1. Text mode   (type your answers — no mic needed)")
    print("  2. Voice mode  (speak your answers — mic required)")
    choice = input("\nEnter 1 or 2: ").strip()

    if choice == "2":
        await run_voice_demo()
    else:
        await run_text_demo()

if __name__ == "__main__":
    asyncio.run(main())
