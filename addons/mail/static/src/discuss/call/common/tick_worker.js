/* eslint-env worker */
/* eslint-disable no-restricted-globals */

let intervalId = null;
let awaitingTock = false;
let isRunning = false;

function reset() {
    if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
    }
    awaitingTock = false;
    isRunning = false;
}

function startProcessing(fps) {
    if (isRunning) {
        return;
    }
    isRunning = true;
    intervalId = setInterval(() => {
        if (awaitingTock) {
            return;
        }
        awaitingTock = true;
        self.postMessage({ command: "tick" });
    }, Math.floor(1000 / (fps || 30)));
}

self.onmessage = (e) => {
    if (!e.data?.command) {
        return;
    }
    const { command, fps } = e.data;
    switch (command) {
        case "start":
            startProcessing(fps);
            break;
        case "tock":
            awaitingTock = false;
            break;
        case "stop":
            reset();
            break;
        default:
            break;
    }
};

self.onmessageerror = () => {
    awaitingTock = false;
};

self.onerror = reset;
