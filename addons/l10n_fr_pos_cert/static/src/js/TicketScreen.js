odoo.define('l10n_fr_pos_cert.TicketScreen', function(require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');

    const PosFrCertTicketScreen = TicketScreen => class extends TicketScreen {
        shouldHideDeleteButton(order) {
            return this.env.pos.is_french_country() && !order.is_empty() || super.shouldHideDeleteButton(order);
        }
    };
    Registries.Component.extend(TicketScreen, PosFrCertTicketScreen);

    return PosFrCertTicketScreen;
});
