/* global chrome */

import { throttle } from "./utils.js";

const ACTIVE_APP_ICON = "/assets/icons/active_icon.png";
const INACTIVE_APP_ICON = "/assets/icons/inactive_icon.png";

// ServiceWorker can be terminated at any time, storage session is
// used to ensure local state is not lost.
chrome.storage.session.set({ isTalkingByTabId: {} });

chrome.tabs.onRemoved.addListener(async (tabId) => {
    const { isTalkingByTabId } = await chrome.storage.session.get();
    delete isTalkingByTabId[tabId];
    await chrome.storage.session.set({ isTalkingByTabId });
    await updateAppIcon();
});

chrome.action.onClicked.addListener(function () {
    chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
});

async function updateAppIcon() {
    const { isTalkingByTabId } = await chrome.storage.session.get();
    const isTalking = Object.values(isTalkingByTabId).some(Boolean);
    chrome.action.setIcon({ path: isTalking ? ACTIVE_APP_ICON : INACTIVE_APP_ICON });
}

chrome.runtime.onMessage.addListener(async function (request, sender) {
    const { from, type, value } = request;
    if (from !== "discuss") {
        return;
    }
    switch (type) {
        case "subscribe":
            {
                const { isTalkingByTabId } = await chrome.storage.session.get();
                isTalkingByTabId[sender.tab.id] = false;
                await chrome.storage.session.set({ isTalkingByTabId });
            }
            break;
        case "unsubscribe":
            {
                const { isTalkingByTabId } = await chrome.storage.session.get();
                delete isTalkingByTabId[sender.tab.id];
                await chrome.storage.session.set({ isTalkingByTabId });
                await updateAppIcon();
            }
            break;
        case "is-talking":
            {
                const { isTalkingByTabId } = await chrome.storage.session.get();
                isTalkingByTabId[sender.tab.id] = value;
                await chrome.storage.session.set({ isTalkingByTabId });
                await updateAppIcon();
            }
            break;
        case "ask-is-enabled":
            chrome.tabs.sendMessage(sender.tab.id, {
                from: "discuss-push-to-talk",
                type: "answer-is-enabled",
            });
            break;
    }
});

async function onCommand(command) {
    const { isTalkingByTabId } = await chrome.storage.session.get();
    for (const tabId of Object.keys(isTalkingByTabId)) {
        switch (command) {
            case "toggle-voice":
                chrome.tabs.sendMessage(Number(tabId), {
                    from: "discuss-push-to-talk",
                    type: "toggle-voice",
                });
                break;
            case "ptt-pressed":
                chrome.tabs.sendMessage(Number(tabId), {
                    from: "discuss-push-to-talk",
                    type: "push-to-talk-pressed",
                });
                break;
        }
    }
}

chrome.commands.onCommand.addListener(throttle(onCommand, 150));
