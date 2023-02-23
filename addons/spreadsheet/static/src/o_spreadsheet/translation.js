/** @odoo-module **/

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { _t } from "@web/core/l10n/translation";

const { args, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

functionRegistry.add("_t", {
    description: _t("Get the translated value of the given string"),
    args: args(`
        value (string) ${_t("Value to translate.")}
    `),
    compute: function (value) {
        return _t(toString(value));
    },
    returns: ["STRING"],
});
