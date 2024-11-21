import { browser } from "@web/core/browser/browser";
import { Record } from "./record";

export class ChatHub extends Record {
    BUBBLE = 56; // same value as $o-mail-ChatHub-bubblesWidth
    BUBBLE_START = 15; // same value as $o-mail-ChatHub-bubblesStart
    BUBBLE_LIMIT = 7;
    BUBBLE_OUTER = 10; // same value as $o-mail-ChatHub-bubblesMargin
    WINDOW_GAP = 10; // for a single end, multiply by 2 for left and right together.
    WINDOW_INBETWEEN = 5;
    WINDOW = 360; // same value as $o-mail-ChatWindow-width
    WINDOW_LARGE = 510; // same value as $o-mail-ChatWindow-widthLarge

    /** @returns {import("models").ChatHub} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChatHub|import("models").ChatHub[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    isBig = Record.attr(false, {
        compute() {
            return browser.localStorage.getItem("mail.user_setting.chat_window_big") === "true";
        },
        onUpdate() {
            /** @this {import("models").ChatHub} */
            if (this.isBig) {
                browser.localStorage.setItem(
                    "mail.user_setting.chat_window_big",
                    this.isBig.toString()
                );
            } else {
                browser.localStorage.removeItem("mail.user_setting.chat_window_big");
            }
        },
    });
    compact = false;
    /** From left to right. Right-most will actually be folded */
    opened = Record.many("ChatWindow", {
        inverse: "hubAsOpened",
        /** @this {import("models").ChatHub} */
        onAdd(r) {
            this.onRecompute();
        },
        /** @this {import("models").ChatHub} */
        onDelete() {
            this.onRecompute();
        },
    });
    /** From top to bottom. Bottom-most will actually be hidden */
    folded = Record.many("ChatWindow", {
        inverse: "hubAsFolded",
        /** @this {import("models").ChatHub} */
        onAdd(r) {
            this.onRecompute();
        },
        /** @this {import("models").ChatHub} */
        onDelete() {
            this.onRecompute();
        },
    });

    closeAll() {
        [...this.opened, ...this.folded].forEach((cw) => cw.close());
    }

    onRecompute() {
        while (this.opened.length > this.maxOpened) {
            const cw = this.opened.pop();
            this.folded.unshift(cw);
        }
    }

    get maxOpened() {
        const chatBubblesWidth = this.BUBBLE_START + this.BUBBLE + this.BUBBLE_OUTER * 2;
        const startGap = this.store.env.services.ui.isSmall ? 0 : this.WINDOW_GAP;
        const endGap = this.store.env.services.ui.isSmall ? 0 : this.WINDOW_GAP;
        const available = browser.innerWidth - startGap - endGap - chatBubblesWidth;
        const maxAmountWithoutHidden = Math.max(
            1,
            Math.floor(
                available / ((this.isBig ? this.WINDOW_LARGE : this.WINDOW) + this.WINDOW_INBETWEEN)
            )
        );
        return maxAmountWithoutHidden;
    }

    get maxFolded() {
        const chatBubbleSpace = this.BUBBLE_START + this.BUBBLE + this.BUBBLE_OUTER * 2;
        return Math.min(this.BUBBLE_LIMIT, Math.floor(browser.innerHeight / chatBubbleSpace));
    }
}

ChatHub.register();
