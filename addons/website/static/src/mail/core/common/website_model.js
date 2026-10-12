import { Record } from "@mail/model/export";

export class Website extends Record {
    static _name = "website";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

Website.register();
