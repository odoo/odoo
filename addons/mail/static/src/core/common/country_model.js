import { Record } from "@mail/core/common/record";

export class Country extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Country>} */
    static records = {};
    /** @returns {import("models").Country} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Country|import("models").Country[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    /** @type {string} */
    code;
    /** @type {number} */
    id;
    /** @type {string} */
    name;

    get flagUrl() {
        return `/base/static/img/country_flags/${encodeURIComponent(this.code.toLowerCase())}.png`;
    }
}

Country.register();
