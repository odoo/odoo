/* global chrome */

window.addEventListener("message", function ({ data }) {
    if (data.from === "discuss") {
        chrome.runtime.sendMessage(data);
    }
});

chrome.runtime.onMessage.addListener(function (request) {
    window.postMessage(request);
});
