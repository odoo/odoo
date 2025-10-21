import { browser } from "@web/core/browser/browser";
import { fields, Record } from "./record";

import { Deferred, Mutex } from "@web/core/utils/concurrency";

export const CHAT_HUB_KEY = "mail.ChatHub";
const CHAT_HUB_COMPACT_LS = "mail.user_setting.chathub_compact";

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
                chatHub.load(ev.newValue);
            } else if (ev.key === null) {
                chatHub.load();
            }
            if (ev.key === CHAT_HUB_COMPACT_LS) {
                chatHub.compact = ev.newValue === "true";
            }
        });
        chatHub
            .load(browser.localStorage.getItem(CHAT_HUB_KEY) ?? undefined)
            .then(() => chatHub.initPromise.resolve());
        return chatHub;
    }

    compact = fields.Attr(false, {
        compute() {
            return browser.localStorage.getItem(CHAT_HUB_COMPACT_LS) === "true";
        },
        /** @this {import("models").Chathub} */
        onUpdate() {
            if (this.compact) {
                browser.localStorage.setItem(CHAT_HUB_COMPACT_LS, this.compact.toString());
            } else {
                browser.localStorage.removeItem(CHAT_HUB_COMPACT_LS);
            }
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
        for (const chatWindow of [...this.opened, ...this.folded]) {
            promises.push(chatWindow.close({ notifyState: false }));
        }
        await Promise.all(promises);
        this.save(); // sync only once at the end
    }

    hideAll() {
        for (const chatWindow of this.opened) {
            chatWindow.bypassCompact = false;
        }
        this.compact = true;
    }

    onRecompute() {
        while (this.opened.length > this.maxOpened) {
            const chatWindow = this.opened.pop();
            this.folded.unshift(chatWindow);
        }
    }

    async load(str = "{}") {
        await this.loadMutex.exec(() => this._load(str));
    }

    async _load(str) {
        /** @type {{ opened: Object[], folded: Object[] }} */
        const { opened = [], folded = [] } = JSON.parse(str);
        const getChannel = (data) => this.store["discuss.channel"].getOrFetch(data.id);
        const openPromises = opened.map(getChannel);
        const foldPromises = folded.map(getChannel);
        this.preFirstFetchPromise.resolve();
        const foldChannels = await Promise.all(foldPromises);
        const openChannels = await Promise.all(openPromises);
        /** @param {import("models").Channel[]} channels */
        const insertChatWindows = (channels) =>
            channels
                .filter((channel) => channel?.exists())
                .map((channel) => this.store.ChatWindow.insert({ channel }));
        const toFold = insertChatWindows(foldChannels);
        const toOpen = insertChatWindows(openChannels);
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
                opened: this.opened.map((chatWindow) => ({ id: chatWindow.channel.id })),
                folded: this.folded.map((chatWindow) => ({ id: chatWindow.channel.id })),
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
