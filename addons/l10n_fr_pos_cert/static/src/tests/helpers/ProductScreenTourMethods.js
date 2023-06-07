odoo.define('l10n_pos_fr_cert.tour.ProductScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do, Check, Execute } = require('point_of_sale.tour.ProductScreenTourMethods');

    class CheckExt extends Check {
        OldUnitPriceIsShown(old) {
            return [
                {
                    content: `check old unit price is shown`,
                    trigger: `li.info:contains(' Old unit price: ')`,
                },
                {
                    content: `check old unit price value`,
                    trigger: `li.info:contains('${old}')`,
                }
            ];
        }
    }
    return createTourMethods('ProductScreen', Do, CheckExt, Execute);
});
