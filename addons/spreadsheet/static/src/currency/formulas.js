/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CellErrorType, helpers, registries } from "@odoo/o-spreadsheet";
const { arg, toString, toJsDate } = helpers;
const { functionRegistry } = registries;

functionRegistry.add("ODOO.CURRENCY.RATE", {
    description: _t(
        "This function takes in two currency codes as arguments, and returns the exchange rate from the first currency to the second as float."
    ),
    category: "Odoo",
    compute: function (currencyFrom, currencyTo, date) {
        const from = toString(currencyFrom);
        const to = toString(currencyTo);
        const _date = date ? toJsDate(date, this.locale) : undefined;
        const rate = this.getters.getCurrencyRate(from, to, _date);
        if (rate.value === false) {
            return {
                value: CellErrorType.GenericError,
                message: _t("Currency rate unavailable."),
            };
        }
        return rate;
    },
    args: [
        arg("currency_from (string)", _t("First currency code.")),
        arg("currency_to (string)", _t("Second currency code.")),
        arg("date (date, optional)", _t("Date of the rate.")),
    ],
    returns: ["NUMBER"],
});
