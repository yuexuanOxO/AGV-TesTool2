let taskQueue = [];
let taskCounter = 0;

function waitPywebviewApi(timeout = 5000) {
  return new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) {
      return resolve(window.pywebview.api);
    }
    const onReady = () => resolve(window.pywebview.api);
    window.addEventListener('pywebviewready', onReady, { once: true });

    let elapsed = 0;
    const t = setInterval(() => {
      if (window.pywebview && window.pywebview.api) {
        clearInterval(t);
        window.removeEventListener('pywebviewready', onReady);
        resolve(window.pywebview.api);
      }
      elapsed += 50;
      if (elapsed >= timeout) {
        clearInterval(t);
        window.removeEventListener('pywebviewready', onReady);
        resolve(null);
      }
    }, 50);
  });
}

// === 任務管理 ===
function addTask(bin, action, buttonEl) {
  taskCounter++;
  taskQueue.push({ id: bin, binTask: action, order: taskCounter });

  // 顯示順序編號
  const label = document.createElement("span");
  label.className = "task-order";
  label.innerText = taskCounter;
  buttonEl.parentNode.appendChild(label);
}

function showTaskModal() {
  if (taskQueue.length === 0) {
    alert("尚未選擇任務！");
    return;
  }

  const list = taskQueue.map(t => `${t.order}. ${t.id} → ${t.binTask}`).join("<br>");
  const html = `
    <div id="taskModal" class="modal">
      <h3>確認任務清單</h3>
      <div>${list}</div>
      <button onclick="startQueue()">✅ 確認無誤，執行任務</button>
      <button onclick="closeModal()">❌ 關閉</button>
    </div>
  `;
  document.body.insertAdjacentHTML("beforeend", html);
}

function closeModal() {
  const m = document.getElementById("taskModal");
  if (m) m.remove();
}

function startQueue() {
  if (taskQueue.length === 0) {
    closeModal();
    return;
  }

  const current = taskQueue[0];
  const ip = new URLSearchParams(location.search).get("ip");

  window.pywebview.api.dispatch_task(ip, current.id, current.binTask, "SELF_POSITION")
    .then(res => {
      if (res && res.ok) {
        console.log(`已下發任務 → ${current.id} ${current.binTask}`);
        pollUntilComplete(ip);
      } else {
        alert("下發失敗: " + (res && res.error ? res.error : "未知錯誤"));
        taskQueue.shift();
        startQueue();
      }
    });

  closeModal();
}

function pollUntilComplete(ip) {
  const interval = setInterval(() => {
    window.pywebview.api.get_task_status(ip).then(statusRes => {
      if (statusRes.ok) {
        const ts = statusRes.resp.task_status_package || {};
        const list = ts.task_status_list || [];
        if (list.length > 0) {
          const latest = list[list.length - 1];
          if ([4, 5, 6].includes(latest.status)) { // COMPLETED/FAILED/CANCELED
            clearInterval(interval);
            taskQueue.shift();
            startQueue();
          }
        }
      }
    });
  }, 2000);
}

// === 主程式 ===
window.addEventListener("DOMContentLoaded", async () => {
  const params = new URLSearchParams(location.search);
  const ip = params.get("ip") || "未知 IP";
  const mapName = params.get("map") || "default";
  const md5 = params.get("md5") || "";

  const title = document.getElementById("title");
  const binsWrap = document.getElementById("binsWrap");
  title.innerText = `目前操作的是 AGV: ${ip}`;

  const api = await waitPywebviewApi(5000);
  if (!api) {
    binsWrap.innerText = "錯誤：pywebview API 尚未就緒";
    return;
  }

  try {
    const res = await api.get_bins(ip, mapName, md5, false);
    if (res && res.ok) {
      const bins = res.bins || {};
      binsWrap.innerHTML = "";

      const entries = Object.entries(bins);
      if (entries.length === 0) {
        binsWrap.innerText = "沒有解析到庫位。";
        return;
      }

      entries.forEach(([point, binDict]) => {
        const section = document.createElement("div");
        section.className = "bin-section";
        section.innerHTML = `<h2>站點 ${point}</h2>`;

        Object.entries(binDict || {}).forEach(([binName, actions]) => {
          const div = document.createElement("div");
          div.className = "bin";

          const titleSpan = document.createElement("span");
          titleSpan.innerText = `庫位 ${binName} → `;
          div.appendChild(titleSpan);

          (actions || []).forEach(action => {
            const btn = document.createElement("button");
            btn.className = "btn action-btn";
            btn.innerText = action;
            btn.addEventListener("click", () => addTask(binName, action, btn));
            div.appendChild(btn);
          });

          section.appendChild(div);
        });

        binsWrap.appendChild(section);
      });

      // === 插入下發任務按鈕 ===
      const sendBtn = document.createElement("button");
      sendBtn.className = "btn primary";
      sendBtn.innerText = "下發任務";
      sendBtn.addEventListener("click", showTaskModal);
      binsWrap.before(sendBtn);

      pollStatus(ip);

    } else {
      binsWrap.innerText = "取得庫位失敗：" + (res && res.error ? res.error : "未知錯誤");
    }
  } catch (err) {
    binsWrap.innerText = "錯誤：" + err;
  }
});


async function pollStatus(ip) {
  try {
    const res = await window.pywebview.api.get_task_status(ip);
    console.log("get_task_status 回傳：", res);

    if (res && res.ok) {
      const pkg = res.resp.task_status_package || {};
      const list = pkg.task_status_list || [];
      let latest = list.length > 0 ? list[list.length - 1] : null;

      const stateMap = {
        0: "NONE",
        1: "WAITING",
        2: "RUNNING",
        3: "SUSPENDED",
        4: "COMPLETED",
        5: "FAILED",
        6: "CANCELED"
      };

      // 只更新對應的 span，不會閃整段
      document.getElementById("navStatus").innerText =
        latest ? stateMap[latest.status] || latest.status : "NONE";
      document.getElementById("taskState").innerText =
        latest ? stateMap[latest.status] || latest.status : "-";
    } else {
      document.getElementById("navStatus").innerText = "ERROR";
      document.getElementById("taskState").innerText = "-";
    }
  } catch (err) {
    console.error("pollStatus 錯誤:", err);
    document.getElementById("navStatus").innerText = "錯誤";
    document.getElementById("taskState").innerText = "-";
  }

  setTimeout(() => pollStatus(ip), 2000);
}
