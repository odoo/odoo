import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

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
    jumpThreadPresent = 0;
    hidden = false;
    /** Whether the chat window was created from the messaging menu */
    fromMessagingMenu = false;
    hubAsOpened = Record.one("ChatHub", {
        /** @this {import("models").ChatWindow} */
        onAdd() {
            this.hubAsFolded = undefined;
        },
    });
    hubAsFolded = Record.one("ChatHub", {
        /** @this {import("models").ChatWindow} */
        onAdd() {
            this.hubAsOpened = undefined;
        },
    });

    get displayName() {
        return this.thread?.displayName;
    }

    get isOpen() {
        return Boolean(this.hubAsOpened);
    }

    async close(options = {}) {
        const { escape = false } = options;
        const chatHub = this.store.chatHub;
        const indexAsOpened = chatHub.opened.findIndex((w) => w.eq(this));
        if (this.thread) {
            this.thread.state = "closed";
        }
        await this._onClose(options);
        this.delete();
        if (escape && indexAsOpened !== -1 && chatHub.opened.length > 0) {
            chatHub.opened[indexAsOpened === 0 ? 0 : indexAsOpened - 1].focus();
        }
    }

    focus() {
        this.autofocus++;
        this.jumpThreadPresent++;
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
        if (this.thread.model === "discuss.channel") {
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
