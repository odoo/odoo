import { fields, Record } from "@mail/core/common/record";

/** @typedef {{ thread?: import("models").Thread }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "thread";

    actionsDisabled = false;
    bypassCompact = false;
    thread = fields.One("Thread", { inverse: "chat_window" });
    autofocus = 0;
    jumpToNewMessage = 0;
    hidden = false;
    /** Whether the chat window was created from the messaging menu */
    fromMessagingMenu = false;
    hubAsOpened = fields.One("ChatHub", { inverse: "opened" });
    hubAsFolded = fields.One("ChatHub", { inverse: "folded" });
    hubAsCanShowOpened = fields.One("ChatHub", {
        inverse: "canShowOpened",
        /** @this {import("models").ChatWindow} */
        compute() {
            if (this.canShow && this.hubAsOpened) {
                return this.store.chatHub;
            }
        },
    });
    hubAsCanShowFolded = fields.One("ChatHub", {
        inverse: "canShowFolded",
        /** @this {import("models").ChatWindow} */
        compute() {
            if (this.canShow && this.hubAsFolded) {
                return this.store.chatHub;
            }
        },
    });

    get displayName() {
        return this.thread?.displayName;
    }

    get isOpen() {
        return Boolean(this.hubAsOpened);
    }

    canShow = fields.Attr(true, {
        compute() {
            return this.computeCanShow();
        },
    });

    computeCanShow() {
        if (this.store.env.services.ui.isSmall) {
            return !this.hubAsFolded || !this.store.discuss?.isActive;
        }
        return !this.store.discuss?.isActive;
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

    async open({
        focus = false,
        notifyState = true,
        jumpToNewMessage = false,
        swapOpened = true,
    } = {}) {
        await this.store.chatHub.initPromise;
        this.store.env.bus.trigger("ChatWindow:will-open");
        this.store.chatHub.folded.delete(this);
        if (swapOpened || !this.store.chatHub.opened.includes(this)) {
            this.store.chatHub.opened.delete(this);
            this.store.chatHub.opened.unshift(this);
        }
        if (notifyState) {
            this.store.chatHub.save();
        }
        if (focus) {
            this.focus({ jumpToNewMessage });
        }
    }

    _onClose() {}
}

ChatWindow.register();
