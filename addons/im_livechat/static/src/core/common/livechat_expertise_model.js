import { Record } from "@mail/core/common/record";

export class LivechatExpertise extends Record {
    static id = "id";
    static _name = "im_livechat.expertise";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
LivechatExpertise.register();
