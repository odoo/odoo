odoo.define('l10n_de_pos_res_cert.pos', function(require) {
    "use strict";

    const models = require('point_of_sale.models');

    const _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        isRestaurantCountryGermany() {
            return this.isCountryGermany() && this.config.module_pos_restaurant;
        },
        //@Override
        disallowLineQuantityChange() {
            let result = _super_posmodel.disallowLineQuantityChange();
            return this.isRestaurantCountryGermany() || result;
        }
    });
});
