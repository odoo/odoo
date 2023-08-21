odoo.define("l10n_sa_edi_pos.models", function (require) {
    "use strict";

    const models = require("point_of_sale.models");
    const _super_order = models.Order.prototype;

    models.Order = models.Order.extend({
        initialize: function () {
            _super_order.initialize.apply(this, arguments);
            if (this.pos.company.country && this.pos.company.country.code === 'SA') {
                this.set_to_invoice(true);
            }
        },
    });
});
