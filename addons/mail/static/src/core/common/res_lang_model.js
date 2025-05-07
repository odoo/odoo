import { Record } from "@mail/core/common/record";

export class ResLang extends Record {
    static id = "id";
    static _name = "res.lang";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResLang.register();
