/** @param {ScrollOptions["behavior"]} behavior */
function scrollToBottomOfPage(behavior) {
    document.body.scrollIntoView({ block: "end", behavior });
}

function isViewAtBottomOfPage() {
    const viewBottomY = window.scrollY + window.visualViewport.height;
    return Math.abs(document.body.scrollHeight - viewBottomY) < 5;
}

/** @param {string} text */
function setLogText(text) {
    const logsElement = document.getElementById("logs");
    const existingText = logsElement.textContent;
    if (existingText !== text) {
        const shouldScroll = !existingText || isViewAtBottomOfPage();
        logsElement.textContent = text;
        if (shouldScroll) {
            scrollToBottomOfPage(existingText ? "smooth" : "instant");
        }
    }
}

async function getLogs() {
    try {
        const result = await fetch("/iot_drivers/iot_logs");
        if (!result.ok) {
            console.warn(`IoT box returned an error (${result.status} ${result.statusText})`);
            return;
        }
        const data = await result.json();
        setLogText(data.logs);
    } catch (error) {
        console.warn(`IoT box is unreachable: ${error}`);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    setInterval(getLogs, 1000);
});
