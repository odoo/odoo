import { Record } from "@mail/core/common/record";

export class LivechatConversationTag extends Record {
    static _name = "im_livechat.conversation.tag";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {number} */
    color;
}
LivechatConversationTag.register();
