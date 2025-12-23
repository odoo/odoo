import { fields, Record } from "@mail/model/export";

/** @typedef {{ thread?: import("models").Thread }} ChatWindowData */

export class ChatWindow extends Record {
    static id = "channel";

    actionsDisabled = false;
    bypassCompact = false;
    channel = fields.One("discuss.channel", { inverse: "chatWindow" });
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

    /**
     * Determine whether this chat window can be closed. May involve
     * user interaction, such as showing a confirmation dialog. This
     * method is only called as a part of {@link requestClose}.
     */
    async _canClose() {
        return true;
    }

    /**
     * Optional tasks to run right before the chat window is closed.
     * This method is only called as a part of {@link requestClose}.
     */
    async _onBeforeClose() {}

    /**
     * Attempt to close this chat window:
     * - First, asks if the window is allowed to close ({@link _canClose}).
     * - Then runs any pre-close tasks ({@link _onBeforeClose}).
     * - Finally, performs the technical close.
     *
     * @param {object} [options={}] Forwarded to {@link ChatWindow.close}
     */
    async requestClose(options) {
        await this.store.chatHub.initPromise;
        this.actionsDisabled = true;
        const canClose = await this._canClose();
        if (!this.exists()) {
            return;
        }
        if (!canClose) {
            this.autofocus++;
            this.actionsDisabled = false;
            return;
        }
        await this._onBeforeClose();
        if (this.exists()) {
            this.close(options);
        }
    }

    /**
     * Perform the technical close of the chat window. This method
     * should __never__ be overridden. To execute code before the chat
     * window is closed, override `_onBeforeClose`. To determine if
     * the chat window should be closed, override `_canClose`.
     *
     * @param {object} [options={}]
     * @param {boolean} [options.notifyState=true] Whether to save the
     * chat hub state after closing.
     * @param {boolean} [options.escape=false] Whether the close was
     * triggered by an escape action.
     */
    close(options = {}) {
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

    _onClose(options) {}
}

ChatWindow.register();
