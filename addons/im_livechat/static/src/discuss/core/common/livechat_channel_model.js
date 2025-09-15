import { Record } from "@mail/core/common/record";

export class LivechatChannel extends Record {
    static _name = "im_livechat.channel";
    static id = "id";

    /** @type {boolean} */
    are_you_inside;
    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
LivechatChannel.register();
