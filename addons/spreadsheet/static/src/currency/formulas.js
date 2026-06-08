import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
const { arg, toString, toJsDate, toNumber } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

functionRegistry.add("ODOO.CURRENCY.RATE", {
    description: _t(
        "This function takes in two currency codes as arguments, and returns the exchange rate from the first currency to the second as float."
    ),
    category: "Odoo",
    compute: function (currencyFrom, currencyTo, date, companyId) {
        const from = toString(currencyFrom);
        const to = toString(currencyTo);
        const _date = date ? toJsDate(date, this.locale) : undefined;
        const _companyId = companyId ? toNumber(companyId) : undefined;
        return this.getters.getCurrencyRate(from, to, _date, _companyId);
    },
    args: [
        arg("currency_from (string)", _t("First currency code.")),
        arg("currency_to (string)", _t("Second currency code.")),
        arg("date (date, optional)", _t("Date of the rate.")),
        arg("company_id (number, optional)", _t("The company to take the exchange rate from.")),
    ],
    returns: ["NUMBER"],
});
