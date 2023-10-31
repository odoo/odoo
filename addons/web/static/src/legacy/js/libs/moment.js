/**
 * This file aim to contains the update/fix we have to do on moment.js localizations.
 * By using updateLocale and/or defineLocale here, we avoid adding change in the official
 * moment.js files, which could lead to conflict when updating the library.
 */

 odoo.define('web.moment.extensions', function () {
    'use strict';
    const locale = moment.locale();
    moment.updateLocale('ca', {
        preparse: function (string) {
            return string.replace(/\b(?:d’|de )(gener|febrer|març|abril|maig|juny|juliol|agost|setembre|octubre|novembre|desembre)/g, '$1');
        }
    });
    if(locale !== 'ca'){
        moment.locale(locale);
    }
});
