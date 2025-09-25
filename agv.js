// agv.js
function waitPywebviewApi(timeout = 5000) {
  return new Promise((resolve) => {
    // 已就緒
    if (window.pywebview && window.pywebview.api) {
      return resolve(window.pywebview.api);
    }
    // 事件版（pywebview 會在注入完成後觸發）
    const onReady = () => resolve(window.pywebview.api);
    window.addEventListener('pywebviewready', onReady, { once: true });

    // 安全保險：輪詢 + 超時
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

  const title = document.getElementById("title");
  const binsWrap = document.getElementById("binsWrap");
  title.innerText = `目前操作的是 AGV: ${ip}`;

  const api = await waitPywebviewApi(5000);
  if (!api) {
    binsWrap.innerText = "錯誤：pywebview API 尚未就緒（window.pywebview.api 為空）。";
    return;
  }

  try {
    const res = await api.get_bins(ip, mapName);
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
          div.innerText = `庫位 ${binName} → 動作 ${Array.isArray(actions) ? actions.join(", ") : ""}`;
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
