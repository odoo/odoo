async function getLogs() {
    try {
        const result = await fetch("/iot_drivers/iot_logs");
        if (!result.ok) {
            console.warn(`IoT box returned an error (${result.status} ${result.statusText})`);
            return;
        }
        const data = await result.json();
        document.getElementById("logs").innerText = data.logs;
        document.getElementById("logs").scrollTop = document.getElementById("logs").scrollHeight;
    } catch (error) {
        console.warn(`IoT box is unreachable: ${error}`);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    setInterval(getLogs, 1000);
});
