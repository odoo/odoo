import { Record } from "@mail/model/export";

export class LivechatExpertise extends Record {
    static id = "id";
    static _name = "im_livechat.expertise";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
LivechatExpertise.register();
