import { Store } from "@mail/core/common/store_service";
import { Record } from "@mail/core/common/record";

import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

const { DateTime } = luxon;

export class ChannelMember extends Record {
    static _name = "discuss.channel.member";
    static id = "id";
    /** @type {Object.<number, import("models").ChannelMember>} */
    static records = {};
    /** @returns {import("models").ChannelMember} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").ChannelMember[] : import("models").ChannelMember}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {string} */
    create_date;
    /** @type {number} */
    id;
    /** @type {luxon.DateTime} */
    last_interest_dt = Record.attr(undefined, { type: "datetime" });
    /** @type {luxon.DateTime} */
    last_seen_dt = Record.attr(undefined, { type: "datetime" });
    persona = Record.one("Persona", { inverse: "channelMembers" });
    thread = Record.one("Thread", { inverse: "channel_member_ids" });
    threadAsSelf = Record.one("Thread", {
        compute() {
            if (this.store.self?.eq(this.persona)) {
                return this.thread;
            }
        },
    });
    fetched_message_id = Record.one("mail.message");
    seen_message_id = Record.one("mail.message");
    /** @deprecated */
    syncUnread = true;
    /** @deprecated */
    _syncUnread = Record.attr(false, {
        compute() {
            if (!this.syncUnread || !this.eq(this.thread?.selfMember)) {
                return false;
            }
            return (
                this.localNewMessageSeparator !== this.new_message_separator ||
                this.localMessageUnreadCounter !== this.message_unread_counter
            );
        },
        onUpdate() {
            if (this._syncUnread) {
                this.localNewMessageSeparator = this.new_message_separator;
                this.localMessageUnreadCounter = this.message_unread_counter;
            }
        },
    });
    /** @deprecated */
    unreadSynced = Record.attr(true, {
        compute() {
            return this.localNewMessageSeparator === this.new_message_separator;
        },
        onUpdate() {
            if (this.unreadSynced) {
                this.hideUnreadBanner = false;
            }
        },
    });
    /** @deprecated */
    hideUnreadBanner = false;
    /** @deprecated */
    localMessageUnreadCounter = 0;
    /** @deprecated */
    localNewMessageSeparator = null;
    message_unread_counter = Record.attr(0, {
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            if (
                this.message_unread_counter === 0 ||
                !this.thread?.isDisplayed ||
                this.thread?.scrollTop !== "bottom" ||
                this.thread.markedAsUnread ||
                !this.thread.isFocused
            ) {
                this.message_unread_counter_ui = this.message_unread_counter;
            }
        },
    });
    message_unread_counter_ui = 0;
    message_unread_counter_bus_id = 0;
    new_message_separator = Record.attr(null, {
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            if (!this.thread?.isDisplayed) {
                this.new_message_separator_ui = this.new_message_separator;
            }
        },
    });
    new_message_separator_ui = null;
    isTyping = false;
    is_typing_dt = Record.attr(undefined, {
        type: "datetime",
        onUpdate() {
            browser.clearTimeout(this.typingTimeoutId);
            if (!this.is_typing_dt) {
                this.isTyping = false;
            }
            if (this.isTyping) {
                this.typingTimeoutId = browser.setTimeout(
                    () => (this.isTyping = false),
                    Store.OTHER_LONG_TYPING
                );
            }
        },
    });
    threadAsTyping = Record.one("Thread", {
        compute() {
            return this.isTyping ? this.thread : undefined;
        },
        eager: true,
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    typingTimeoutId;

    get name() {
        return this.thread.getPersonaName(this.persona);
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }

    get memberSince() {
        return this.create_date ? deserializeDateTime(this.create_date) : undefined;
    }

    /**
     * @param {import("models").Message} message
     */
    hasSeen(message) {
        return this.persona.eq(message.author) || this.seen_message_id?.id >= message.id;
    }
    get lastSeenDt() {
        return this.last_seen_dt
            ? this.last_seen_dt.toLocaleString(DateTime.TIME_24_SIMPLE, {
                  locale: user.lang,
              })
            : undefined;
    }

    /** @deprecated */
    get totalUnreadMessageCounter() {
        let counter = this.message_unread_counter;
        if (!this.unreadSynced) {
            counter += this.localMessageUnreadCounter;
        }
        return counter;
    }
}

ChannelMember.register();
