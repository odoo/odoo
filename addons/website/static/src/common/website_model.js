import { Record } from "@mail/core/common/record";

export class Website extends Record {
    static id = "id";
    static _name = "website";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

Website.register();
