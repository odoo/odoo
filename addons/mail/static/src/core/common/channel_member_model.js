import { Record } from "@mail/core/common/record";
import { OTHER_LONG_TYPING } from "@mail/discuss/typing/common/typing_service";
import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class ChannelMember extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").ChannelMember>} */
    static records = {};
    /** @returns {import("models").ChannelMember} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChannelMember|import("models").ChannelMember[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {string} */
    create_date;
    /** @type {number} */
    id;
    /** @type {luxon.DateTime} */
    last_interest_dt = Record.attr(undefined, { type: "datetime" });
    persona = Record.one("Persona", { inverse: "channelMembers" });
    rtcSession = Record.one("RtcSession");
    thread = Record.one("Thread", { inverse: "channelMembers" });
    threadAsSelf = Record.one("Thread", {
        compute() {
            if (this.store.self?.eq(this.persona)) {
                return this.thread;
            }
        },
    });
    fetched_message_id = Record.one("Message");
    seen_message_id = Record.one("Message");
    threadAsTyping = Record.one("Thread", {
        onAdd() {
            browser.clearTimeout(this.typingTimeoutId);
            this.typingTimeoutId = browser.setTimeout(
                () => (this.threadAsTyping = undefined),
                OTHER_LONG_TYPING
            );
        },
        onDelete() {
            browser.clearTimeout(this.typingTimeoutId);
        },
    });
    /** @type {number} */
    typingTimeoutId;

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }

    get memberSince() {
        return this.create_date ? deserializeDateTime(this.create_date) : undefined;
    }
}

ChannelMember.register();
