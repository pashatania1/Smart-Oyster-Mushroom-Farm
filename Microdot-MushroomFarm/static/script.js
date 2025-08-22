    const tempCtx = document.getElementById('tempChart');
    const humiCtx = document.getElementById('humiChart');

    const tempChart = new Chart(tempCtx, {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Suhu (°C)', data: [], borderColor: 'green', fill: false }] },
      options: { responsive: true, animation: { duration: 300 } }
    });

    const humiChart = new Chart(humiCtx, {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Kelembapan (%)', data: [], borderColor: 'blue', fill: false }] },
      options: { responsive: true, animation: { duration: 300 } }
    });

    // Fungsi update device status dengan warna
    function updateDeviceStatus(el, state) {
      el.textContent = state ? "ON" : "OFF";
      el.className = state ? "font-bold text-green-600" : "font-bold text-gray-500";
    }
    
    fetch("/api/user/status")
      .then(res => res.json())
      .then(data => {
        if (data.logged_in) {
          document.getElementById("user-info").innerHTML = `
            <span class="font-semibold">Hai, ${data.username}</span>
            <a href="/logout" class="ml-4 bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-lg">Logout</a>
          `;
        }
      });
      
    // Update data dari API
    async function fetchData() {
      try {
        const res = await fetch('/api/data');
        const data = await res.json();

        document.getElementById('temp').textContent = data.temperature.toFixed(1) + ' °C';
        document.getElementById('humi').textContent = data.humidity.toFixed(1) + ' %';
        document.getElementById('gas').textContent = data.valuegas;
        document.getElementById('water').textContent = data.distance.toFixed(1) + ' cm';

        updateDeviceStatus(document.getElementById('buzzer'), data.databuzz === 1);
        updateDeviceStatus(document.getElementById('fan'), data.datafan === 1);
        updateDeviceStatus(document.getElementById('lamp'), data.datalamp === 1);
        updateDeviceStatus(document.getElementById('mister'), data.datasprinkle === 1);

        const jamurStatusEl = document.getElementById('jamur_status');
        jamurStatusEl.textContent = data.status === "Happy" ? "Jamur HAPPY 😊" : "Jamur tidak tumbuh 😢";
        jamurStatusEl.className = data.status === "Happy" ? "font-bold text-lg text-green-700" : "font-bold text-lg text-red-600";

        const timeLabel = new Date().toLocaleTimeString();
        if (tempChart.data.labels.length > 10) {
          tempChart.data.labels.shift();
          tempChart.data.datasets[0].data.shift();
          humiChart.data.labels.shift();
          humiChart.data.datasets[0].data.shift();
        }
        tempChart.data.labels.push(timeLabel);
        tempChart.data.datasets[0].data.push(data.temperature);
        humiChart.data.labels.push(timeLabel);
        humiChart.data.datasets[0].data.push(data.humidity);

        tempChart.update();
        humiChart.update();

        document.getElementById('mode').textContent = data.mode.charAt(0).toUpperCase() + data.mode.slice(1);
      } catch (err) {
        console.error("Gagal ambil data:", err);
      }
    }

    async function fetchLampStatus() {
      const res = await fetch('/api/lamp/status');
      const data = await res.json();
      updateDeviceStatus(document.getElementById('lamp'), data.status.toUpperCase() === "ON");
    }

    document.getElementById('switchModeBtn').addEventListener('click', async () => {
      try {
        const currentMode = document.getElementById('mode').textContent.toLowerCase();
        const newMode = currentMode === "incubation" ? "fruiting" : "incubation";
        await fetch('/api/mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: newMode })
        });
        fetchData();
      } catch (err) {
        console.error("Gagal switch mode:", err);
      }
    });

    setInterval(fetchData, 5000);
    setInterval(fetchLampStatus, 5000);
    fetchData();
    fetchLampStatus();