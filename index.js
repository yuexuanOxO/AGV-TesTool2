window.addEventListener("DOMContentLoaded", () => {
  const ipInput = document.getElementById("ipInput");
  const btnFetch = document.getElementById("btnFetch");
  const agvList = document.getElementById("agvList");

  // ✅ 讓 Enter 鍵觸發「取得狀態」按鈕
  ipInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      btnFetch.click();
    }
  });

  btnFetch.addEventListener("click", async () => {
    const ip = ipInput.value.trim();
    if (!ip) return;

    agvList.innerHTML = "<div class='agv-row'><div class='col'>搜尋中...</div></div>";

    try {
      let results = [];
      if (ip.split(".").length === 3) {
        // 網段模式
        results = await window.pywebview.api.scan_network(ip);
      } else {
        // 單台 IP
        const res = await window.pywebview.api.get_robot_info(ip);
        if (res.ok) {
          const info = res.resp || {};
          const curMap = info.current_map || "未知地圖";
          // 嘗試從多筆 entries 中找到對應 current_map 的 md5；找不到就取第 0 筆
          const entries = Array.isArray(info.current_map_entries) ? info.current_map_entries : [];
          let md5 = "";
          if (entries.length > 0) {
            const hit = entries.find(e => e && (e.name === curMap));
            md5 = (hit && hit.md5) || (entries[0] && entries[0].md5) || "";
          }
          results = [{
            ip: info.current_ip || ip,
            vehicle_id: info.vehicle_id || "未知ID",
            model: info.model || "未知型號",
            map: curMap,
            map_md5: md5
          }];
        }
      }

      if (results.length > 0) {
        agvList.innerHTML = "";
        results.forEach(info => {
          const row = document.createElement("div");
          row.className = "agv-row";
          row.innerHTML = `
            <div class="col ip">${info.ip}</div>
            <div class="col id">${info.vehicle_id}</div>
            <div class="col model">${info.model}</div>
            <div class="col map">${info.map}</div>
            <div class="col action">
              <button class="btn connect-btn" 
                      data-ip="${info.ip}" 
                      data-map="${info.map}" 
                      data-md5="${info.map_md5 || ''}">連線</button>
            </div>
          `;
          agvList.appendChild(row);
        });

        // 綁定「連線」按鈕事件的地方，改用 currentTarget 取屬性
        document.querySelectorAll(".connect-btn").forEach(btn => {
          btn.addEventListener("click", e => {
            const targetIp = e.currentTarget.getAttribute("data-ip");
            const map = e.currentTarget.getAttribute("data-map") || "default";
            const md5 = e.currentTarget.getAttribute("data-md5") || "";
            if (targetIp) {
              window.location.href =
                `agv.html?ip=${encodeURIComponent(targetIp)}&map=${encodeURIComponent(map)}&md5=${encodeURIComponent(md5)}`;
            }
          });
        });


      } else {
        agvList.innerHTML = "<div class='agv-row'><div class='col'>沒有找到 AGV</div></div>";
      }

    } catch (err) {
      agvList.innerHTML = "<div class='agv-row'><div class='col'>錯誤：" + err + "</div></div>";
    }
  });
});
