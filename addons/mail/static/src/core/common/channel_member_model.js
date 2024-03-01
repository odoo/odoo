import { Record } from "@mail/core/common/record";
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
    persona = Record.one("Persona", { inverse: "channelMembers" });
    rtcSession = Record.one("RtcSession");
    thread = Record.one("Thread", { inverse: "channelMembers" });
    threadAsSelf = Record.one("Thread", {
        compute() {
            if (this._store.self?.eq(this.persona)) {
                return this.thread;
            }
        },
    });
    fetched_message_id = Record.one("Message");
    seen_message_id = Record.one("Message");

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
