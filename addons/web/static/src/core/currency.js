/** @odoo-module **/

import { session } from "@web/session";

export const currencies = session.currencies || {};
// to make sure code is reading currencies from here
delete session.currencies;

export function getCurrency(id) {
    return currencies[id];
}
