/* global chrome */

(async () => {
    window.addEventListener("message", function ({ data }) {
        if (data.from === "discuss") {
            chrome.runtime.sendMessage(data);
        }
    });
})();
