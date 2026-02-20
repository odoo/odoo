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
    /** @type {string} */
    custom_channel_name;
    /**
     * false means using the custom_notifications from user settings.
     *
     * @type {false|"all"|"mentions"|"no_notif"}
     */
    custom_notifications;
    /** @type {number} */
    id;
    is_pinned = fields.Attr(undefined, {
        compute() {
            return (
                !this.unpin_dt ||
                (this.last_interest_dt && this.last_interest_dt >= this.unpin_dt) ||
                (this.channel_id?.last_interest_dt &&
                    this.channel_id?.last_interest_dt >= this.unpin_dt)
            );
        },
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            this.channel_id?.onPinStateUpdated();
        },
    });
    last_interest_dt = fields.Datetime();
    last_seen_dt = fields.Datetime();
    guest_id = fields.One("mail.guest");
    partner_id = fields.One("res.partner");
    get persona() {
        return this.partner_id || this.guest_id;
    }
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
    mute_until_dt = fields.Datetime();
    new_message_separator = fields.Attr(null, {
        /** @this {import("models").ChannelMember} */
        onUpdate() {
            if (!this.channel_id?.isDisplayed) {
                this.new_message_separator_ui = this.new_message_separator;
            }
        },
    });
    new_message_separator_ui = null;
    isTyping = fields.Attr(false, {
        onUpdate() {
            browser.clearTimeout(this.typingTimeoutId);
            if (this.isTyping) {
                this.registerTypingTimeout();
            }
        },
    });
    is_typing_dt = fields.Datetime({
        onUpdate() {
            browser.clearTimeout(this.typingTimeoutId);
            if (
                !this.is_typing_dt ||
                DateTime.now().diff(this.is_typing_dt).milliseconds > Store.OTHER_LONG_TYPING
            ) {
                this.isTyping = false;
            }
            if (this.isTyping) {
                this.registerTypingTimeout();
            }
        },
    });
    registerTypingTimeout() {
        this.typingTimeoutId = browser.setTimeout(
            () => (this.isTyping = false),
            Store.OTHER_LONG_TYPING
        );
    }
    threadAsTyping = fields.One("Thread", {
        compute() {
            return this.isTyping ? this.channel_id : undefined;
        },
        eager: true,
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    typingTimeoutId;
    unpin_dt = fields.Datetime();

    get name() {
        if (this.guest_id) {
            return this.guest_id.name;
        }
        return this.channel_id.getPersonaName(this.partner_id);
    }

    get avatarUrl() {
        return this.partner_id?.avatarUrl || this.guest_id?.avatarUrl;
    }

    get im_status() {
        return this.partner_id?.im_status || this.guest_id?.im_status;
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
