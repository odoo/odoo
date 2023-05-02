odoo.define("@odoo/o-spreadsheet", ["@web/core/l10n/translation"], function (require) {
    "use strict";
    const { _t } = require("@web/core/l10n/translation");
    const spreadsheet = window.o_spreadsheet;
    spreadsheet.setTranslationMethod(_t);
    return spreadsheet;
});
