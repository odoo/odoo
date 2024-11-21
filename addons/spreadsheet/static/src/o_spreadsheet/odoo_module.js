// @odoo-module ignore

odoo.define(
    "@odoo/o-spreadsheet",
    ["@web/core/l10n/translation", "@spreadsheet/o_spreadsheet/o_spreadsheet"],
    function (require) {
        "use strict";
        const { _t, translationLoaded, translatedTerms } = require("@web/core/l10n/translation");
        const spreadsheet = require("@spreadsheet/o_spreadsheet/o_spreadsheet");
        window.o_spreadsheet = spreadsheet;
        spreadsheet.setTranslationMethod(_t, () => translatedTerms[translationLoaded]);
        return spreadsheet;
    }
);
