import { fields, Record } from "@mail/core/common/record";
import { isMobileOS } from "@web/core/browser/feature_detection";

/** @typedef {{ thread?: import("models").Thread }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "thread";

    actionsDisabled = false;
    bypassCompact = false;
    thread = fields.One("Thread");
    autofocus = 0;
    jumpToNewMessage = 0;
    hidden = false;
    /** Whether the chat window was created from the messaging menu */
    fromMessagingMenu = false;
    hubAsOpened = fields.One("ChatHub", { inverse: "opened" });
    hubAsFolded = fields.One("ChatHub", { inverse: "folded" });

    get displayName() {
        return this.thread?.displayName;
    }

    get isOpen() {
        return Boolean(this.hubAsOpened);
    }

    async close(options = {}) {
        await this.store.chatHub.initPromise;
        const { escape = false } = options;
        options.notifyState ??= true;
        const chatHub = this.store.chatHub;
        const indexAsOpened = chatHub.opened.findIndex((w) => w.eq(this));
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.folded.delete(this);
        if (options.notifyState) {
            this.store.chatHub.save();
        }
        if (escape && indexAsOpened !== -1 && chatHub.opened.length > 0) {
            chatHub.opened[indexAsOpened === 0 ? 0 : indexAsOpened - 1].focus();
        }
        this._onClose(options);
        this.delete();
    }

    focus({ jumpToNewMessage = false } = {}) {
        this.autofocus++;
        if (jumpToNewMessage) {
            this.jumpToNewMessage++;
        }
    }

    async fold() {
        await this.store.chatHub.initPromise;
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.folded.delete(this);
        this.store.chatHub.folded.unshift(this);
        this.store.chatHub.save();
        this.bypassCompact = false;
    }

    async open({ focus = false, notifyState = true, jumpToNewMessage = false } = {}) {
        await this.store.chatHub.initPromise;
        this.store.chatHub.folded.delete(this);
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.opened.unshift(this);
        if (notifyState) {
            this.store.chatHub.save();
        }
        if (focus && !isMobileOS()) {
            this.focus({ jumpToNewMessage });
        }
    }

    _onClose() {}
}

ChatWindow.register();
