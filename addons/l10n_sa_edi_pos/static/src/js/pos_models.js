odoo.define("l10n_sa_edi_pos.models", function (require) {
    "use strict";

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const L10nSAPosOrder = (Order) => class L10nSAPosOrder extends Order {
        constructor() {
            super(...arguments);
            if (this.pos.company.country && this.pos.company.country.code === 'SA') {
                this.set_to_invoice(true);
            }
        }
    }

    Registries.Model.extend(Order, L10nSAPosOrder);
});
