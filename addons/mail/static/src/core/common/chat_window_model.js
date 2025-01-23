import { Record } from "@mail/core/common/record";
import { isMobileOS } from "@web/core/browser/feature_detection";

/** @typedef {{ thread?: import("models").Thread }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "thread";
    /** @type {Object<number, import("models").ChatWindow} */
    static records = {};
    /** @returns {import("models").ChatWindow} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChatWindow|import("models").ChatWindow[]} */
    static insert() {
        return super.insert(...arguments);
    }

    actionsDisabled = false;
    thread = Record.one("Thread");
    autofocus = 0;
    hidden = false;
    /** Whether the chat window was created from the messaging menu */
    fromMessagingMenu = false;
    hubAsOpened = Record.one("ChatHub", { inverse: "opened" });
    hubAsFolded = Record.one("ChatHub", { inverse: "folded" });

    get displayName() {
        return this.thread?.displayName;
    }

    get isOpen() {
        return Boolean(this.hubAsOpened);
    }

    close(options = {}) {
        const { escape = false, notifyState = true } = options;
        const chatHub = this.store.chatHub;
        const indexAsOpened = chatHub.opened.findIndex((w) => w.eq(this));
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.folded.delete(this);
        if (notifyState) {
            this.store.chatHub.save();
        }
        if (escape && indexAsOpened !== -1 && chatHub.opened.length > 0) {
            chatHub.opened[indexAsOpened === 0 ? 0 : indexAsOpened - 1].focus();
        }
        this._onClose();
        this.delete();
    }

    focus() {
        this.autofocus++;
    }

    fold() {
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.folded.delete(this);
        this.store.chatHub.folded.unshift(this);
        this.store.chatHub.save();
    }

    open({ focus = false, notifyState = true } = {}) {
        this.store.chatHub.folded.delete(this);
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.opened.unshift(this);
        if (notifyState) {
            this.store.chatHub.save();
        }
        if (focus && !isMobileOS()) {
            this.focus();
        }
    }

    _onClose() {}
}

ChatWindow.register();
