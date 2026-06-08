import { Record } from "@mail/model/export";

export class ResLang extends Record {
    static _name = "res.lang";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {string} */
    code;
    /** Returns the base language code without region or locale (e.g. en_US → en) */
    get baseCode() {
        return this.code?.split(/[_@]/)[0];
    }
}

ResLang.register();
