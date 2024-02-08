import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

import { _t } from "@web/core/l10n/translation";

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

    thread = Record.one("Thread");
    autofocus = 0;
    hidden = false;
    /** Whether the chat window was created from the messaging menu */
    fromMessagingMenu = false;
    hubAsActuallyOpened = Record.one("ChatHub", {
        /** @this {import("models").ChatWindow} */
        onDelete() {
            if (!this.thread && !this.hubAsActuallyOpened) {
                this.delete();
            }
        },
    });
    hubAsOpened = Record.one("ChatHub");
    hubAsFolded = Record.one("ChatHub");

    get displayName() {
        return this.thread?.displayName ?? _t("New message");
    }

    get isOpen() {
        return Boolean(this.hubAsActuallyOpened);
    }

    async close(options = {}) {
        const { escape = false } = options;
        const chatHub = this.store.chatHub;
        const indexAsOpened = chatHub.actuallyOpened.findIndex((w) => w.eq(this));
        const thread = this.thread;
        if (thread) {
            thread.state = "closed";
        }
        await this._onClose(options);
        this.delete();
        if (escape && indexAsOpened !== -1 && chatHub.actuallyOpened.length > 0) {
            if (indexAsOpened === chatHub.actuallyOpened.length - 1) {
                chatHub.actuallyOpened.at(indexAsOpened - 1).focus();
            } else {
                chatHub.actuallyOpened.at(indexAsOpened).focus();
            }
        }
    }

    focus() {
        this.autofocus++;
    }

    fold() {
        if (!this.thread) {
            return this.close();
        }
        this.store.chatHub.folded.delete(this);
        this.store.chatHub.folded.unshift(this);
        this.thread.state = "folded";
        this.notifyState();
    }

    open({ notifyState = true } = {}) {
        this.store.chatHub.opened.delete(this);
        this.store.chatHub.opened.unshift(this);
        if (this.thread) {
            this.thread.state = "open";
            if (notifyState) {
                this.notifyState();
            }
        }
        this.focus();
    }

    notifyState() {
        if (
            this.store.env.services.ui.isSmall ||
            this.thread?.isTransient ||
            !this.thread?.hasSelfAsMember
        ) {
            return;
        }
        if (this.thread?.model === "discuss.channel") {
            this.thread.foldStateCount++;
            return rpc(
                "/discuss/channel/fold",
                {
                    channel_id: this.thread.id,
                    state: this.thread.state,
                    state_count: this.thread.foldStateCount,
                },
                { shadow: true }
            );
        }
    }

    async _onClose({ notifyState = true } = {}) {
        if (notifyState) {
            this.notifyState();
        }
    }
}

ChatWindow.register();
