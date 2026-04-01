import { Record } from "@mail/core/common/record";

export class Country extends Record {
    static id = "id";
    static _name = "res.country";

    /** @type {string} */
    code;
    /** @type {number} */
    id;
    /** @type {string} */
    name;

    get flagUrl() {
        if (!this.code) {
            return false;
        }
        return `/base/static/img/country_flags/${encodeURIComponent(this.code.toLowerCase())}.png`;
    }
}

Country.register();
