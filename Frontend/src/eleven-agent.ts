import { Conversation } from "@elevenlabs/client";

declare const chrome: any;

let conversation: Conversation | null = null;
let pageUrl: string | null = null;

async function startAgent() {
  if (conversation) return;

  const startButton = document.getElementById("start-agent") as HTMLButtonElement | null;
  const statusEl = document.getElementById("agent-status");

  try {
    if (statusEl) statusEl.textContent = "Connecting to ElevenLabs agent...";

    conversation = await Conversation.startSession({
      agentId: "agent_0701kard2ss4e1c8f3z78gb8jv0a",
      connectionType: "webrtc",
      workletPaths: {
        rawAudioProcessor: chrome.runtime.getURL(
          "dist/rawAudioProcessor.worklet.js"
        ),
        audioConcatProcessor: chrome.runtime.getURL(
          "dist/audioConcatProcessor.worklet.js"
        ),
      },
    });

    if (statusEl) statusEl.textContent = "Agent connected. Explaining the page...";

    // 🔥 Auto-tell the agent what page the user is on
    if (pageUrl && conversation && "sendUserMessage" in conversation) {
      await (conversation as any).sendUserMessage(
        `The user is currently viewing this web page: ${decodeURIComponent(
          pageUrl
        )}. 
Please explain this website to them in simple, accessible language. Start with a short summary, then offer to go into more detail if they want.`
      );
    }

    if (startButton) {
      startButton.disabled = true;
      startButton.textContent = "Listening...";
    }
  } catch (err) {
    console.error("Failed to start ElevenLabs conversation", err);
    if (statusEl) statusEl.textContent = "Error connecting to agent. Check console.";
  }
}


function stopAgent() {
  if (conversation) {
    conversation.endSession();
    conversation = null;
  }
  const startButton = document.getElementById("start-agent") as HTMLButtonElement | null;
  const statusEl = document.getElementById("agent-status");

  if (statusEl) statusEl.textContent = "Agent disconnected.";
  if (startButton) {
    startButton.disabled = false;
    startButton.textContent = "Start explaining";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const params = new URL(window.location.href).searchParams;
  pageUrl = params.get("url");

  const statusEl = document.getElementById("agent-status");
  if (statusEl && pageUrl) {
    statusEl.textContent = `Ready to explain the page!`;
  }

  const startBtn = document.getElementById("start-agent");
  const stopBtn = document.getElementById("stop-agent");

  if (startBtn) {
    startBtn.addEventListener("click", () => {
      void startAgent();
    });
  }
  if (stopBtn) {
    stopBtn.addEventListener("click", () => {
      stopAgent();
    });
  }
});

