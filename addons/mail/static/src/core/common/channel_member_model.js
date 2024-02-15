import { Record } from "@mail/core/common/record";

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

    /** @type {number} */
    id;
    persona = Record.one("Persona", { inverse: "channelMembers" });
    rtcSession = Record.one("RtcSession");
    thread = Record.one("Thread", { inverse: "channelMembers" });
    fetched_message_id = Record.one("Message");
    seen_message_id = Record.one("Message");

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
