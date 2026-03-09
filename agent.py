"""
CxBolt Voice Bot — LiveKit Agent (Full Production Mode)
Connects to a real phone number via Twilio + LiveKit SIP.
Run this AFTER you've set up LiveKit and Twilio.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cxbolt-agent")

# LiveKit Agents imports
try:
    from livekit import agents, rtc
    from livekit.agents import AgentSession, Agent, RoomInputOptions
    from livekit.plugins import openai as lk_openai, silero
except ImportError:
    print("❌ LiveKit not installed. Run: pip install livekit-agents livekit-plugins-silero livekit-plugins-openai")
    exit(1)

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Sarah, a friendly and professional insurance qualification agent calling from Insurance Solutions.

Your ONLY job is to follow this exact qualification script. Do NOT deviate from it.

SCRIPT:
1. Greet the person warmly and introduce yourself as Sarah from Insurance Solutions.
2. Explain you're calling because they may qualify for affordable health insurance.
3. Ask if they want to find out if they qualify.
4. If YES → proceed with qualification questions one at a time.
5. If NO → politely thank them and end the call.

QUALIFICATION QUESTIONS (ask one at a time, wait for answer before asking next):
Q1: Are you between the ages of 19 and 64? (need YES to qualify)
Q2: Is your annual income below $30,000? (need YES to qualify)
Q3: Are you a U.S. citizen or permanent resident? (need YES to qualify)
Q4: Do you currently have Medicare, Medicaid, veterans' benefits, employer-sponsored insurance, or any marketplace/ACA/Obamacare coverage? (need NO to qualify)
Q5: Have you enrolled in a marketplace plan within the last 60 days? (need NO to qualify)

QUALIFICATION OUTCOMES:
- All answers match → "Great news! You appear to qualify. Let me connect you with a specialist who can get you enrolled today." Then transfer.
- Any disqualifying answer → "I understand. Based on your answers, you may not qualify for this particular plan right now. Thank you so much for your time, have a wonderful day!"
- Unclear/unsure answer → gently ask them to clarify with yes or no.

RULES:
- Keep ALL responses SHORT — this is a phone call.
- Never ask more than one question at a time.
- Be warm, professional, and patient.
- If asked about cost → say "It's designed to be very affordable — the specialist can give you exact details."
- If they want to be removed from the list → apologize and say you'll remove them."""

# ─── AGENT CLASS ──────────────────────────────────────────────────────────────

class InsuranceQualificationAgent(Agent):
    def __init__(self):
        super().__init__(instructions=SYSTEM_PROMPT)

    async def on_enter(self):
        """Called when agent joins a room/call — start the conversation."""
        await self.session.say(
            "Hello! This is Sarah calling from Insurance Solutions. How are you today? "
            "I'm reaching out because you may qualify for an affordable health insurance plan. "
            "Would you like to find out if you qualify?"
        )


# ─── ENTRYPOINT ───────────────────────────────────────────────────────────────

async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint — called by LiveKit for each incoming call."""
    logger.info(f"New call received: room={ctx.room.name}")

    await ctx.connect()

    # Set up the LLM — using Ollama via OpenAI-compatible API
    llm = lk_openai.LLM.with_ollama(
        model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    )

    # Set up STT — Faster-Whisper via a compatible plugin
    # Note: You can swap this for any STT plugin
    from livekit.plugins import openai as lk_openai_stt
    stt = lk_openai_stt.STT.with_whisper(
        model="base.en",
        language="en",
    )

    # Set up TTS — using macOS say or a custom TTS
    # For production, swap with ElevenLabs or Cartesia plugin
    tts = lk_openai.TTS(
        model="tts-1",
        voice="nova",
        base_url=os.getenv("TTS_BASE_URL", "http://localhost:5000/v1"),  # local TTS server
    )

    # Create and start the agent session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=InsuranceQualificationAgent(),
        room_input_options=RoomInputOptions(
            noise_cancellation=True,
        ),
    )

    logger.info("Agent session started successfully")


# ─── RUN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=agents.WorkerType.ROOM,
        )
    )
