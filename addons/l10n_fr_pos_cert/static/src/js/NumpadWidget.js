odoo.define('l10n_fr_pos_cert.NumpadWidget', function (require) {
    'use strict';

    const { patch } = require('web.utils');
    const NumpadWidget = require('point_of_sale.NumpadWidget');

    patch(NumpadWidget.prototype, 'l10n_fr_pos_cert', {
        get hasPriceControlRights() {
            return this.env.model.isFrenchCountry() ? false : this._super();
        },
    });

    return NumpadWidget;
});
