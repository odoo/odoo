import { browser } from "@web/core/browser/browser";
import { Record } from "./record";

import { Mutex } from "@web/core/utils/concurrency";

export const CHAT_HUB_KEY = "mail.ChatHub";

export class ChatHub extends Record {
    BUBBLE = 56; // same value as $o-mail-ChatHub-bubblesWidth
    BUBBLE_START = 15; // same value as $o-mail-ChatHub-bubblesStart
    BUBBLE_LIMIT = 7;
    BUBBLE_OUTER = 10; // same value as $o-mail-ChatHub-bubblesMargin
    WINDOW_GAP = 10; // for a single end, multiply by 2 for left and right together.
    WINDOW_INBETWEEN = 5;
    WINDOW = 380; // same value as $o-mail-ChatWindow-width

    /** @returns {import("models").ChatHub} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChatHub|import("models").ChatHub[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new() {
        const chatHub = super.new(...arguments);
        this.store.isReady.then(() => {
            browser.addEventListener("storage", (ev) => {
                if (ev.key === CHAT_HUB_KEY) {
                    chatHub.load(ev.newValue);
                } else if (ev.key === null) {
                    chatHub.load();
                }
            });
            chatHub.load(browser.localStorage.getItem(CHAT_HUB_KEY) ?? undefined);
        });
        return chatHub;
    }

    compact = false;
    /** From left to right. Right-most will actually be folded */
    opened = Record.many("ChatWindow", {
        inverse: "hubAsOpened",
        /** @this {import("models").ChatHub} */
        onAdd(r) {
            this.onRecompute();
        },
    });
    /** From top to bottom. Bottom-most will actually be hidden */
    folded = Record.many("ChatWindow", { inverse: "hubAsFolded" });
    loadMutex = new Mutex();

    closeAll() {
        for (const cw of [...this.opened, ...this.folded]) {
            cw.close({ notifyState: false });
        }
        this.save(); // sync only once at the end
    }

    init() {
        const { opened = [], folded = [] } = JSON.parse(
            browser.localStorage.getItem(CHAT_HUB_KEY) ?? "{}"
        );
        for (const threadData of [...opened, ...folded]) {
            this.initThread(threadData);
        }
    }

    initThread(threadData) {
        this.store.fetchStoreData("mail.thread", {
            thread_model: threadData.model,
            thread_id: threadData.id,
            request_list: ["display_name"],
        });
    }

    onRecompute() {
        while (this.opened.length > this.maxOpened) {
            const cw = this.opened.pop();
            this.folded.unshift(cw);
        }
    }

    load(str = "{}") {
        this.loadMutex.exec(() => this._load(str));
    }

    async _load(str) {
        const { opened = [], folded = [] } = JSON.parse(str);
        const openCandidates = [];
        const foldCandidates = [];
        const promises = [];
        for (const threadData of opened) {
            promises.push(
                this.store.Thread.getOrFetch(threadData).then((thread) => {
                    if (thread) {
                        openCandidates.push(this.store.ChatWindow.insert({ thread }));
                    }
                })
            );
        }
        for (const threadData of folded) {
            promises.push(
                this.store.Thread.getOrFetch(threadData).then((thread) => {
                    if (thread) {
                        foldCandidates.push(this.store.ChatWindow.insert({ thread }));
                    }
                })
            );
        }
        await Promise.all(promises);
        // state might change while waiting for all data to be loaded
        const toFold = foldCandidates.filter((chatWindow) => chatWindow.exists());
        const toOpen = openCandidates.filter((chatWindow) => chatWindow.exists());
        // close first to make room for others
        for (const chatWindow of [...this.opened, ...this.folded]) {
            if (chatWindow.notIn(toOpen) && chatWindow.notIn(toFold)) {
                chatWindow.close({ notifyState: false });
            }
        }
        // folded before opened because if there are too many opened they will be added to folded
        this.folded = toFold.filter((chatWindow) => chatWindow.exists());
        this.opened = toOpen.filter((chatWindow) => chatWindow.exists());
    }

    get maxOpened() {
        const chatBubblesWidth = this.BUBBLE_START + this.BUBBLE + this.BUBBLE_OUTER * 2;
        const startGap = this.store.env.services.ui.isSmall ? 0 : this.WINDOW_GAP;
        const endGap = this.store.env.services.ui.isSmall ? 0 : this.WINDOW_GAP;
        const available = browser.innerWidth - startGap - endGap - chatBubblesWidth;
        const maxAmountWithoutHidden = Math.max(
            1,
            Math.floor(available / (this.WINDOW + this.WINDOW_INBETWEEN))
        );
        return maxAmountWithoutHidden;
    }

    get maxFolded() {
        const chatBubbleSpace = this.BUBBLE_START + this.BUBBLE + this.BUBBLE_OUTER * 2;
        return Math.min(this.BUBBLE_LIMIT, Math.floor(browser.innerHeight / chatBubbleSpace));
    }

    save() {
        browser.localStorage.setItem(
            CHAT_HUB_KEY,
            JSON.stringify({
                opened: this.opened.map((cw) => ({ id: cw.thread.id, model: cw.thread.model })),
                folded: this.folded.map((cw) => ({ id: cw.thread.id, model: cw.thread.model })),
            })
        );
    }
}

ChatHub.register();
