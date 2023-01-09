/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
const { args, toString, toJSDate } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;


functionRegistry
    .add("ODOO.CURRENCY.RATE", {
        description: _t("This function takes in two currency codes as arguments, and returns the exchange rate from the first currency to the second as float."),
        compute: function (currencyFrom, currencyTo, date) {
            const from = toString(currencyFrom);
            const to = toString(currencyTo);
            const _date = date ? toJSDate(date) : undefined;
            return this.getters.getCurrencyRate(from, to, _date);
        },
        args: args(`
            currency_from (string) ${_t("First currency code.")}
            currency_to (string) ${_t("Second currency code.")}
            date (date, optional) ${_t("Date of the rate.")}
        `),
    returns: ["NUMBER"],
});
