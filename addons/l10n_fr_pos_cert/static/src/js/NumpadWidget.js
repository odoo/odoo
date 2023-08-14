odoo.define('l10n_fr_pos_cert.NumpadWidget', function(require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const PosFrNumpadWidget = NumpadWidget => class extends NumpadWidget {
        get hasPriceControlRights() {
            if (this.env.pos.is_french_country()) {
                return false;
            } else {
                return super.hasPriceControlRights;
            }
        }
    };

    Registries.Component.extend(NumpadWidget, PosFrNumpadWidget);

    return NumpadWidget;
 });
