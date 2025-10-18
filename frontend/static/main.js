const form = document.getElementById("chat-form");
const chatLog = document.getElementById("chat-log");

function appendMessage(role, text) {
  const message = document.createElement("div");
  message.className = "message";
  message.innerHTML = `<span class="label">${role}:</span> <span>${text}</span>`;
  chatLog.appendChild(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const topic = document.getElementById("topic").value;
  const affection = parseInt(document.getElementById("affection").value, 10);
  const userMessageInput = document.getElementById("user");
  const userMessage = userMessageInput.value.trim();

  if (!userMessage) {
    return;
  }

  appendMessage("You", userMessage);
  userMessageInput.value = "";

  const payload = {
    topic,
    affection,
    user: userMessage,
  };

  try {
    form.querySelector("button").disabled = true;
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    appendMessage("Ani", data.reply);
  } catch (error) {
    appendMessage("System", `エラーが発生しました: ${error.message}`);
  } finally {
    form.querySelector("button").disabled = false;
  }
});
