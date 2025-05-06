import { Store } from "@mail/core/common/store_service";
import { fields, Record } from "@mail/core/common/record";

import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

const { DateTime } = luxon;

export class ChannelMember extends Record {
    static _name = "discuss.channel.member";
    static id = "id";

    /** @type {string} */
    create_date;
    /** @type {number} */
    id;
    last_interest_dt = fields.Datetime();
    last_seen_dt = fields.Datetime();
    persona = fields.One("Persona", { inverse: "channelMembers" });
    channel_id = fields.One("Thread", { inverse: "channel_member_ids" });
    threadAsSelf = fields.One("Thread", {
        compute() {
            if (this.store.self?.eq(this.persona)) {
                return this.channel_id;
            }
        },
    });
    fetched_message_id = fields.One("mail.message");
    seen_message_id = fields.One("mail.message");
    hideUnreadBanner = false;
    message_unread_counter = fields.Attr(0, {
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            if (
                this.message_unread_counter === 0 ||
                !this.channel_id?.isDisplayed ||
                this.channel_id?.scrollTop !== "bottom" ||
                this.channel_id.markedAsUnread ||
                !this.channel_id.isFocused
            ) {
                this.message_unread_counter_ui = this.message_unread_counter;
            }
        },
    });
    message_unread_counter_ui = 0;
    message_unread_counter_bus_id = 0;
    new_message_separator = fields.Attr(null, {
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            if (!this.channel_id?.isDisplayed) {
                this.new_message_separator_ui = this.new_message_separator;
            }
        },
    });
    new_message_separator_ui = null;
    threadAsTyping = fields.One("Thread", {
        compute() {
            return this.isTyping ? this.channel_id : undefined;
        },
        eager: true,
        onAdd() {
            browser.clearTimeout(this.typingTimeoutId);
            this.typingTimeoutId = browser.setTimeout(
                () => (this.isTyping = false),
                Store.OTHER_LONG_TYPING
            );
        },
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    typingTimeoutId;

    get name() {
        return this.channel_id.getPersonaName(this.persona);
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
}

ChannelMember.register();
