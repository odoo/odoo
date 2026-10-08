import { Record } from "@mail/model/export";

export class LivechatChannel extends Record {
    /** @type {"im_livechat.channel"} */
    static _name = "im_livechat.channel";

    /** @type {boolean} */
    are_you_inside;
    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
LivechatChannel.register();
