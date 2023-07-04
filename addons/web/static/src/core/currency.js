/** @odoo-module **/

import { session } from "@web/session";

export const currencies = session.currencies || {};
// to make sure code is reading currencies from here
delete session.currencies;

export function getCurrency(id) {
    if (id && ((currencies && currencies[id]) || (currencies.currencies && currencies.currencies[id]))) {
        return currencies[id]? currencies[id]:
        currencies.currencies[id]? currencies.currencies[id]: false;
    }
    return false;
}

export function getCurrencySymbol(id) {
    if (id && ((currencies && currencies[id]) || (currencies.currencies && currencies.currencies[id]))) {
        return currencies[id]? currencies[id].symbol:
        currencies.currencies[id]? currencies.currencies[id].symbol: false;
    }
    return false;
}

