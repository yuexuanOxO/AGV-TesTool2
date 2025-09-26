window.addEventListener("DOMContentLoaded", () => {
  const ipInput = document.getElementById("ipInput");
  const btnFetch = document.getElementById("btnFetch");
  const agvList = document.getElementById("agvList");

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
          results = [{
            ip: res.resp.current_ip || ip,
            vehicle_id: res.resp.vehicle_id || "未知ID",
            model: res.resp.model || "未知型號",
            map: res.resp.current_map || "未知地圖"
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
            <button class="btn connect-btn" data-ip="${info.ip}" data-map="${info.map}">連線</button>
            </div>
          `;
          agvList.appendChild(row);
        });

        // 綁定所有「連線」按鈕
        document.querySelectorAll(".connect-btn").forEach(btn => {
          btn.addEventListener("click", e => {
            const targetIp = e.target.getAttribute("data-ip");
            const map = e.currentTarget.getAttribute("data-map") || "default";
            if (targetIp) {
              window.location.href = `agv.html?ip=${encodeURIComponent(targetIp)}&map=${encodeURIComponent(map)}`;

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
