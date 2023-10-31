/* global chrome */

import { throttle } from "./utils.js";

// ServiceWorker can be terminated at any time, storage session is
// used to ensure local state is not lost.
chrome.storage.session.set({ activeTabIds: [], talkingTabIds: [] });

chrome.tabs.onRemoved.addListener(async (tabId) => {
    await setIsTalking(tabId, false);
    const activeTabIds = new Set((await chrome.storage.session.get()).activeTabIds);
    activeTabIds.delete(tabId);
    chrome.storage.session.set({ activeTabIds: [...activeTabIds] });
});

chrome.action.onClicked.addListener(async function () {
    const shortcutTabs = await chrome.tabs.query({ url: "chrome://extensions/shortcuts" });
    if (shortcutTabs.length > 0) {
        chrome.tabs.update(shortcutTabs[0].id, { selected: true });
        return;
    }
    chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
});

async function setIsTalking(tabId, isTalking) {
    const talkingTabIds = new Set((await chrome.storage.session.get()).talkingTabIds);
    talkingTabIds[isTalking ? "add" : "delete"](tabId);
    await chrome.storage.session.set({ talkingTabIds: [...talkingTabIds] });
    chrome.action.setIcon({
        path: `/assets/icons/icon_${talkingTabIds.size > 0 ? "active" : "inactive"}.png`,
    });
}

chrome.runtime.onMessage.addListener(async function (request, sender) {
    const { from, type, value } = request;
    if (from !== "discuss") {
        return;
    }
    switch (type) {
        case "subscribe":
            {
                const activeTabIds = new Set((await chrome.storage.session.get()).activeTabIds);
                activeTabIds.add(sender.tab.id);
                await chrome.storage.session.set({ activeTabIds: [...activeTabIds] });
            }
            break;
        case "unsubscribe":
            {
                const activeTabIds = new Set((await chrome.storage.session.get()).activeTabIds);
                activeTabIds.delete(sender.tab.id);
                await chrome.storage.session.set({ activeTabIds: [...activeTabIds] });
                await setIsTalking(sender.tab.id, false);
            }
            break;
        case "is-talking":
            await setIsTalking(sender.tab.id, value);
            break;
    }
});

async function onCommand(command) {
    const activeTabIds = (await chrome.storage.session.get()).activeTabIds;
    for (const tabId of activeTabIds) {
        switch (command) {
            case "toggle-voice":
                chrome.scripting.executeScript({
                    target: { tabId },
                    func: () =>
                        window.postMessage({ from: "discuss-push-to-talk", type: "toggle-voice" }),
                });
                break;
            case "ptt-pressed":
                chrome.scripting.executeScript({
                    target: { tabId },
                    func: () =>
                        window.postMessage({
                            from: "discuss-push-to-talk",
                            type: "push-to-talk-pressed",
                        }),
                });
                break;
        }
    }
}

chrome.commands.onCommand.addListener(throttle(onCommand, 150));
