const alertBox = document.getElementById("alert");
const groupSelect = document.getElementById("groupSelect");
const groupsList = document.getElementById("groupsList");
const tasksList = document.getElementById("tasksList");
const messageInput = document.getElementById("message");
const charCount = document.getElementById("charCount");

let groups = [];

function showAlert(message, type = "error") {
  alertBox.textContent = message;
  alertBox.className = "alert " + type;
}

function hideAlert() {
  alertBox.className = "alert hidden";
  alertBox.textContent = "";
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json();

  if (!res.ok || data.success === false) {
    throw new Error(data.error || "Xatolik yuz berdi");
  }

  return data;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function loadGroups() {
  hideAlert();
  groupsList.textContent = "Yuklanmoqda...";
  groupSelect.innerHTML = '<option value="">Guruh tanlang...</option>';

  try {
    const data = await api("/api/groups");
    groups = data.groups || [];

    if (!groups.length) {
      groupsList.textContent = "Guruh yoki kanal topilmadi.";
      return;
    }

    groupsList.innerHTML = "";
    groups.forEach((group) => {
      const option = document.createElement("option");
      option.value = group.id;
      option.textContent = group.title;
      option.dataset.title = group.title;
      groupSelect.appendChild(option);

      const item = document.createElement("div");
      item.className = "item";
      item.innerHTML = `
        <div class="item-title">${escapeHtml(group.title)}</div>
        <div class="item-meta">${escapeHtml(group.type)} · ID: ${escapeHtml(group.id)}</div>
      `;
      groupsList.appendChild(item);
    });
  } catch (err) {
    groupsList.textContent = "Guruhlarni yuklashda xatolik.";
    showAlert(err.message);
  }
}

async function loadTasks() {
  tasksList.textContent = "Yuklanmoqda...";

  try {
    const data = await api("/api/tasks");
    const tasks = data.tasks || [];

    if (!tasks.length) {
      tasksList.textContent = "Hozircha jadvallar mavjud emas.";
      return;
    }

    tasksList.innerHTML = "";

    tasks.forEach((task) => {
      const intervalMin = Math.max(1, Math.round(task.interval_seconds / 60));

      const item = document.createElement("div");
      item.className = "item";
      item.innerHTML = `
        <div class="item-title">${escapeHtml(task.group_title || task.group_id)}</div>
        <div class="item-meta">
          Har ${intervalMin} daqiqa · Keyingi: ${escapeHtml(task.next_run || "-")}
          ${task.last_error ? `<br>Oxirgi xato: ${escapeHtml(task.last_error)}` : ""}
        </div>
        <div class="item-meta">${escapeHtml(task.message.slice(0, 180))}${task.message.length > 180 ? "..." : ""}</div>
        <button class="delete-btn" data-id="${task.task_id}">O‘chirish</button>
      `;
      tasksList.appendChild(item);
    });

    document.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Bu jadval o‘chirilsinmi?")) return;

        try {
          await api(`/api/tasks/${btn.dataset.id}`, {
            method: "DELETE"
          });

          showAlert("Jadval o‘chirildi", "success");
          loadTasks();
        } catch (err) {
          showAlert(err.message);
        }
      });
    });
  } catch (err) {
    tasksList.textContent = "Jadvallarni yuklashda xatolik.";
    showAlert(err.message);
  }
}

messageInput?.addEventListener("input", () => {
  charCount.textContent = messageInput.value.length;
});

document.getElementById("refreshGroups")?.addEventListener("click", loadGroups);
document.getElementById("refreshTasks")?.addEventListener("click", loadTasks);

document.getElementById("scheduleForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert();

  const selected = groupSelect.options[groupSelect.selectedIndex];

  const payload = {
    group_id: groupSelect.value,
    group_title: selected?.dataset?.title || selected?.textContent || "",
    message: messageInput.value.trim(),
    interval: document.getElementById("interval").value,
    interval_type: document.getElementById("intervalType").value
  };

  try {
    await api("/api/schedule", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    messageInput.value = "";
    charCount.textContent = "0";

    showAlert("Jadval muvaffaqiyatli qo‘shildi", "success");
    loadTasks();
  } catch (err) {
    showAlert(err.message);
  }
});

loadGroups();
loadTasks();
