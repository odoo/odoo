import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooUIPlugin } from "@spreadsheet/plugins";

const { arg, toString } = spreadsheet.helpers;
const { functionRegistry, featurePluginRegistry } = spreadsheet.registries;

/**
 * Standard spreadsheet dashboards defined in the source code need to be translated.
 * To achieve this, custom code in translate.py extracts source terms from spreadsheet JSON files
 * (specifically, files matching *.osheet.json).
 * This function is then used to translate those terms at runtime.
 */
export function dynamicSpreadsheetTranslate(term) {
    return _t(term);
}

class TranslationNamespace extends OdooUIPlugin {
    static getters = /** @type {const} */ (["dynamicTranslate"]);

    /**
     * @see dynamicSpreadsheetTranslate
     * @param {string} term
     */
    dynamicTranslate(term) {
        return dynamicSpreadsheetTranslate(term);
    }
}
featurePluginRegistry.add("TranslationNamespace", TranslationNamespace);

functionRegistry.add("_t", {
    description: _t("Get the translated value of the given string"),
    args: [arg("value (string)", _t("Value to translate."))],
    compute: function (value) {
        return this.getters.dynamicTranslate(toString(value));
    },
    returns: ["STRING"],
    hidden: true,
});
