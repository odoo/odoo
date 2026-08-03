import { Record } from "@mail/model/export";

export class ResCurrency extends Record {
    static _name = "res.currency";

    /** @type {number} */
    decimal_places;
    /** @type {number} */
    id;
    /** @type {"after"|"before"} */
    position;
    /** @type {string} */
    symbol;
}

ResCurrency.register();
