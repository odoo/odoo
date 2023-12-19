/** @odoo-module alias=@web/../tests/legacy_tests/patch_localization default=false */

import { localization } from "@web/core/l10n/localization";

Object.assign(localization, {
    dateFormat: "MM/dd/yyyy",
    timeFormat: "HH:mm:ss",
    dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    decimalPoint: ".",
    direction: "ltr",
    grouping: [],
    multiLang: false,
    thousandsSep: ",",
    weekStart: 7,
    code: "en",
});
