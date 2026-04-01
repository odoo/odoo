import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t, appTranslateFn } from "@web/core/l10n/translation";
import { OdooUIPlugin } from "@spreadsheet/plugins";

const { arg, toString } = spreadsheet.helpers;
const { functionRegistry, featurePluginRegistry } = spreadsheet.registries;

/**
 * Standard spreadsheet dashboards defined in the source code need to be translated.
 * To achieve this, custom code in translate.py extracts source terms from spreadsheet JSON files
 * (specifically, files matching *.osheet.json).
 * This function is then used to translate those terms at runtime.
 */
export function dynamicSpreadsheetTranslate(translationNamespace, term) {
    return appTranslateFn(term, translationNamespace);
}

class TranslationNamespace extends OdooUIPlugin {
    static getters = /** @type {const} */ (["dynamicTranslate"]);

    constructor(config) {
        super(config);
        this.translationNamespace = config.custom.translationNamespace;
    }

    /**
     * @see dynamicSpreadsheetTranslate
     * @param {string} term
     */
    dynamicTranslate(term) {
        if (this.translationNamespace) {
            return dynamicSpreadsheetTranslate(this.translationNamespace, term);
        }
        return term;
    }
}
featurePluginRegistry.replace("dynamic_translate", TranslationNamespace);

functionRegistry.add("_t", {
    description: _t("Get the translated value of the given string"),
    args: [arg("value (string)", _t("Value to translate."))],
    compute: function (value) {
        return this.getters.dynamicTranslate(toString(value));
    },
    returns: ["STRING"],
    hidden: true,
});
