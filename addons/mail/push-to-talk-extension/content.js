/* global chrome */

// https://chromewebstore.google.com/detail/discuss-push-to-talk/mdiacebcbkmjjlpclnbcgiepgifcnpmg
const EXT_ID = "mdiacebcbkmjjlpclnbcgiepgifcnpmg";

chrome.runtime.onMessage.addListener(function (request, sender) {
    if (location.origin !== "null" && sender.id === EXT_ID) {
        window.postMessage(request, location.origin);
    }
});
