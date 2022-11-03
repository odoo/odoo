odoo.define("pos_system_user.models", function (require) {
    "use strict";

    const models = require("point_of_sale.models");

    const pos_model = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        push_orders: async function (order, opts) {
            const res = await pos_model.push_orders.apply(this, arguments);
            this.env.pos.trigger('order_synchronized', this.env.pos, order);
            return res
        }
    });

    models.load_fields('res.partner', ['l10n_eg_building_no']);
});