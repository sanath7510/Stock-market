
let fuzzyChart;
let rtChart;

function lineChart(ctx, labels, datasets) {
    return new Chart(ctx, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            stacked: false,
            scales: {
                x: { type: 'time', time: { unit: 'day' } },
                y: { beginAtZero: false }
            },
            plugins: { legend: { position: 'top' } }
        }
    });
}

// --- Fuzzy (page 2 small chart, optional) ---
function updateFuzzyChart(payload) {
    const el = document.getElementById('fuzzyChart');
    if (!el) return;
    const ctx = el.getContext('2d');
    const ds = [{
        label: 'Fuzzy Prediction',
        data: payload.values,
        fill: true,
        borderWidth: 2
    }];
    if (!fuzzyChart) fuzzyChart = lineChart(ctx, payload.labels, ds);
    else {
        fuzzyChart.data.labels = payload.labels;
        fuzzyChart.data.datasets = ds;
        fuzzyChart.update();
    }
}

// --- Real-time page 3 ---
async function fetchRealtime() {
    const el = document.getElementById('realtimeChart');
    if (!el) return;
    const company = el.dataset.ticker || '';
    const res = await fetch(`/realtime-graph-data?ticker=${encodeURIComponent(company)}`);
    const data = await res.json();
    const ctx = el.getContext('2d');

    const datasets = [
        { label: 'Close', data: data.close, borderWidth: 2, fill: false },
        { label: '5d', data: data.ma5, borderWidth: 1, fill: false },
        { label: '42d', data: data.ma42, borderWidth: 1, fill: false },
        { label: '252d', data: data.ma252, borderWidth: 2, fill: false },
    ];
    if (data.predicted) {
        datasets.unshift({ label: 'Fuzzy Price', data: data.predicted, borderWidth: 2, fill: false });
    }
    if (!rtChart) rtChart = lineChart(ctx, data.labels, datasets);
    else {
        rtChart.data.labels = data.labels;
        rtChart.data.datasets = datasets;
        rtChart.update();
    }
}

window.addEventListener('DOMContentLoaded', () => {
    // optional initial fuzzy fetch
    if (document.getElementById('fuzzyChart')) {
        fetch('/fuzzy-graph-data').then(r=>r.json()).then(updateFuzzyChart).catch(console.error);
    }
    fetchRealtime();
    // refresh every 30s
    setInterval(fetchRealtime, 30000);
});
