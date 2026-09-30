import { browser } from "@web/core/browser/browser";
import { fields, Record } from "./record";

import { Deferred, Mutex } from "@web/core/utils/concurrency";

export const CHAT_HUB_KEY = "mail.ChatHub";
export const CHAT_HUB_COMPACT_LS = "mail.user_setting.chathub_compact";

export class ChatHub extends Record {
    BUBBLE = 56; // same value as $o-mail-ChatHub-bubblesWidth
    BUBBLE_START = 15; // same value as $o-mail-ChatHub-bubblesStart
    BUBBLE_LIMIT = 7;
    BUBBLE_OUTER = 10; // same value as $o-mail-ChatHub-bubblesMargin
    WINDOW_GAP = 10; // for a single end, multiply by 2 for left and right together.
    WINDOW_INBETWEEN = 5;
    WINDOW = 380; // same value as $o-mail-ChatWindow-width

    /** @returns {import("models").ChatHub} */
    static new() {
        /** @type {import("models").ChatHub} */
        const chatHub = super.new(...arguments);
        browser.addEventListener("storage", (ev) => {
            if (ev.key === CHAT_HUB_KEY) {
                chatHub.load(ev.newValue || undefined);
            } else if (ev.key === null) {
                chatHub.load();
            }
            if (ev.key === CHAT_HUB_COMPACT_LS) {
                chatHub._recomputeCompact++;
            }
        });
        chatHub
            .load(browser.localStorage.getItem(CHAT_HUB_KEY) ?? undefined)
            .then(() => chatHub.initPromise.resolve());
        return chatHub;
    }
    _recomputeCompact = 0;
    compact = fields.Attr(false, {
        compute() {
            void this._recomputeCompact;
            return browser.localStorage.getItem(CHAT_HUB_COMPACT_LS) === "true";
        },
    });
    canShowOpened = fields.Many("ChatWindow");
    canShowFolded = fields.Many("ChatWindow");
    /** From left to right. Right-most will actually be folded */
    opened = fields.Many("ChatWindow", {
        inverse: "hubAsOpened",
        /** @this {import("models").ChatHub} */
        onAdd(r) {
            this.onRecompute();
        },
    });
    /** From top to bottom. Bottom-most will actually be hidden */
    folded = fields.Many("ChatWindow", { inverse: "hubAsFolded" });
    initPromise = new Deferred();
    preFirstFetchPromise = new Deferred();
    loadMutex = new Mutex();

    async closeAll() {
        await this.initPromise;
        const promises = [];
        for (const cw of [...this.opened, ...this.folded]) {
            promises.push(cw.close({ notifyState: false }));
        }
        await Promise.all(promises);
        this.save(); // sync only once at the end
    }

    hideAll() {
        for (const cw of this.opened) {
            cw.bypassCompact = false;
        }
        browser.localStorage.setItem(CHAT_HUB_COMPACT_LS, true);
        this._recomputeCompact++;
    }

    onRecompute() {
        while (this.opened.length > this.maxOpened) {
            const cw = this.opened.pop();
            this.folded.unshift(cw);
        }
    }

    async load(str = "{}") {
        await this.loadMutex.exec(() => this._load(str));
    }

    async _load(str) {
        /** @type {{ opened: Object[], folded: Object[] }} */
        const { opened = [], folded = [] } = JSON.parse(str);
        const hasInvalidData =
            opened.some((data) => !data.id || !data.model) ||
            folded.some((data) => !data.id || !data.model);
        if (hasInvalidData) {
            opened.length = 0;
            folded.length = 0;
            browser.localStorage.removeItem(CHAT_HUB_KEY);
        }
        const getThread = (data) => this.store.Thread.getOrFetch(data, ["display_name"]);
        const openPromises = opened.map(getThread);
        const foldPromises = folded.map(getThread);
        this.preFirstFetchPromise.resolve();
        const foldThreads = await Promise.all(foldPromises);
        const openThreads = await Promise.all(openPromises);
        /** @param {import("models").Thread[]} threads */
        const insertChatWindows = (threads) =>
            threads
                .filter((thread) => thread?.model === "discuss.channel")
                .map((thread) => this.store.ChatWindow.insert({ thread }));
        const toFold = insertChatWindows(foldThreads);
        const toOpen = insertChatWindows(openThreads);
        // close first to make room for others
        for (const chatWindow of [...this.opened, ...this.folded]) {
            if (chatWindow.notIn(toOpen) && chatWindow.notIn(toFold)) {
                chatWindow.close({ force: true, notifyState: false });
            }
        }
        // folded before opened because if there are too many opened they will be added to folded
        this.folded = toFold;
        this.opened = toOpen;
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

    showConversations = fields.Attr(false, {
        compute() {
            return this.canShowOpened.length + this.canShowFolded.length > 0;
        },
    });
}

ChatHub.register();
