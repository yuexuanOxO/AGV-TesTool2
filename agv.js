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
    binsWrap.innerText = "錯誤：pywebview API 尚未就緒（window.pywebview.api 為空）。";
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

          // 顯示庫位名稱
          const titleSpan = document.createElement("span");
          titleSpan.innerText = `庫位 ${binName} → `;
          div.appendChild(titleSpan);

          // 把每個動作變成按鈕
          (actions || []).forEach(action => {
            const btn = document.createElement("button");
            btn.className = "btn action-btn";
            btn.innerText = action;
            btn.addEventListener("click", () => {
              alert(`點擊了 ${binName} 的 ${action} 動作`);
              // TODO: 之後改成呼叫下發任務 API
              // 例如：window.pywebview.api.dispatch_task(ip, binName, action);
            });
            div.appendChild(btn);
          });

          section.appendChild(div);
        });

        binsWrap.appendChild(section);
      });
    } else {
      binsWrap.innerText = "取得庫位失敗：" + (res && res.error ? res.error : "未知錯誤");
    }
  } catch (err) {
    binsWrap.innerText = "錯誤：" + err;
  }
});
