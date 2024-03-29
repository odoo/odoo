/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { arg, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

functionRegistry.add("_t", {
    description: _t("Get the translated value of the given string"),
    args: [arg("value (string)", _t("Value to translate."))],
    compute: function (value) {
        return _t(toString(value));
    },
    returns: ["STRING"],
    hidden: true,
});
