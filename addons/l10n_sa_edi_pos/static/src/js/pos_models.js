odoo.define("l10n_sa_edi_pos.models", function (require) {
    "use strict";

    var { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const L10nSaOrder = (Order) => class L10nSaOrder extends Order {
        constructor() {
            super(...arguments);
            if (this.pos.company.country && this.pos.company.country.code === 'SA') {
                this.set_to_invoice(true);
            }
        }
    }
    Registries.Model.extend(Order, L10nSaOrder);
});
