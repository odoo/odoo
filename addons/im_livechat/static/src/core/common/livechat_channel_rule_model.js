import { Record } from "@mail/model/record";

export class LivechatChannelRule extends Record {
    static id = "id";
    static _name = "im_livechat.channel.rule";

    /** @type {string} */
    action;
    /** @type {number} */
    autopopup_timer;
    chatbot_script_id = Record.one("chatbot.script");
    /** @type {number} */
    id;
}
LivechatChannelRule.register();
