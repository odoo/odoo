// @odoo-module ignore

odoo.define(
    "@odoo/o-spreadsheet",
    ["@web/core/l10n/translation", "@spreadsheet/o_spreadsheet/o_spreadsheet"],
    function (require) {
        "use strict";
        const { appTranslateFn, translationLoaded, translatedTerms } = require("@web/core/l10n/translation");
        const spreadsheet = require("@spreadsheet/o_spreadsheet/o_spreadsheet");
        window.o_spreadsheet = spreadsheet;
        const _t = (str, ...args) => appTranslateFn(str, "spreadsheet", ...args);
        spreadsheet.setTranslationMethod(_t, () => translatedTerms[translationLoaded]);
        return spreadsheet;
    }
);
