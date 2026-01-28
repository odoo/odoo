import { Record } from "@mail/model/export";

export class ResLang extends Record {
    static _name = "res.lang";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResLang.register();
