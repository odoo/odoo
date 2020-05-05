odoo.define('l10n_fr_pos_cert.NumpadWidget', function(require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const PosFrNumpadWidget = NumpadWidget => class extends NumpadWidget {
        async changeMode(mode) {
            if (this.env.pos.is_french_country() && mode === 'price') {
                await this.showPopup('ErrorPopup', {
                        title: this.env._t('Module error'),
                        body: this.env._t('Adjusting the price is not allowed.'),
                    });
                return;
            } else {
                super.changeMode(mode);
            }
        }
    };

    Registries.Component.extend(NumpadWidget, PosFrNumpadWidget);

    return NumpadWidget;
 });
