const MAX_LOG_LINES = 10000;

/** @param {string} text */
function stripAnsiCodes(text) {
    // eslint-disable-next-line no-control-regex
    return text.replaceAll(/\x1b\[[\w;]+m/g, "");
}

/** @param {string[]} logLines */
function filterLogRequests(logLines) {
    return logLines.filter((line) => !line.includes("GET /iot_drivers/iot_logs"));
}

/** @param {string[]} logLines */
function trimLogs(logLines) {
    if (logLines.length <= MAX_LOG_LINES) {
        return logLines;
    }
    return [
        `[previous ${logLines.length - MAX_LOG_LINES} lines have been trimmed]\n`,
        ...logLines.slice(-MAX_LOG_LINES),
    ];
}

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
    const logLines = trimLogs(filterLogRequests(stripAnsiCodes(text).split("\n")));
    const logText = logLines.join("\n");
    const logsElement = document.getElementById("logs");
    const existingText = logsElement.textContent;
    if (existingText !== logText) {
        const shouldScroll = !existingText || isViewAtBottomOfPage();
        logsElement.textContent = logText;
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
