import { Record } from "@mail/model/export";

export class Country extends Record {
    static _name = "res.country";

    /** @type {string} */
    code;
    /** @type {number} */
    id;
    /** @type {string} */
    image_url;
    /** @type {string} */
    name;
    /** @type {number} */
    phone_code;

    get flagUrl() {
        if (!this.code) {
            return false;
        }
        return `/base/static/img/country_flags/${encodeURIComponent(this.code.toLowerCase())}.png`;
    }
}

Country.register();
