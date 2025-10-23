import { Store } from "@mail/core/common/store_service";
import { DiscussChannelMember } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").ChannelMember} */
function setup() {
    this.channel_id = fields.One("mail.thread", { inverse: "channel_member_ids" });
    this.threadAsSelf = fields.One("mail.thread", {
        compute() {
            if (this.store.self?.eq(this.persona)) {
                return this.channel_id;
            }
        },
    });
    this.hideUnreadBanner = false;
    this.message_unread_counter_ui = 0;
    this.message_unread_counter_bus_id = 0;
    this.new_message_separator_ui = null;
    this.isTyping = false;
    this.is_typing_dt = fields.Datetime({
        onUpdate() {
            browser.clearTimeout(this.typingTimeoutId);
            if (
                !this.is_typing_dt ||
                DateTime.now().diff(this.is_typing_dt).milliseconds > Store.OTHER_LONG_TYPING
            ) {
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
    this.threadAsTyping = fields.One("mail.thread", {
        compute() {
            return this.isTyping ? this.channel_id : undefined;
        },
        eager: true,
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    this.typingTimeoutId;
}

patch(DiscussChannelMember.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
    _compute_is_pinned() {
        return (
            !this.unpin_dt ||
            (this.last_interest_dt && this.last_interest_dt >= this.unpin_dt) ||
            (this.channel_id?.last_interest_dt &&
                this.channel_id?.last_interest_dt >= this.unpin_dt)
        );
    },
    _is_pinned_onUpdate() {
        this.channel_id?.onPinStateUpdated();
    },
    _new_message_separator_onUpdate() {
        if (!this.channel_id?.isDisplayed) {
            this.new_message_separator_ui = this.new_message_separator;
        }
    },
    _message_unread_counter_onUpdate() {
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
    get persona() {
        return this.partner_id || this.guest_id;
    },
    get name() {
        if (this.guest_id) {
            return this.guest_id.name;
        }
        return this.channel_id.getPersonaName(this.partner_id);
    },
    get avatarUrl() {
        return this.partner_id?.avatarUrl || this.guest_id?.avatarUrl;
    },
    get im_status() {
        return this.partner_id?.im_status || this.guest_id?.im_status;
    },
    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    },
    get memberSince() {
        return this.create_date ? this.create_date : undefined;
    },
    /**
     * @param {import("models").Message} message
     */
    hasSeen(message) {
        return this.persona.eq(message.author) || this.seen_message_id?.id >= message.id;
    },
    get lastSeenDt() {
        return this.last_seen_dt
            ? this.last_seen_dt.toLocaleString(DateTime.TIME_24_SIMPLE, {
                  locale: user.lang,
              })
            : undefined;
    },
});

export const ChannelMember = DiscussChannelMember;
