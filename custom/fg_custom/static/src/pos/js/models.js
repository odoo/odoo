odoo.define("fg_custom.is_non_zero_vat", function (require) {
  "use strict";

    const models = require("point_of_sale.models");
    models.load_fields("account.tax", "is_non_zero_vat");
    var _super_orderline = models.Orderline;

     models.Orderline = models.Orderline.extend({
        export_for_printing: function () {
            var result = _super_orderline.prototype.export_for_printing.apply(this, arguments);
            var product =  this.get_product();
            var taxes = this.get_taxes();
//            var taxes_ids = this.tax_ids || product.taxes_id;
//            taxes_ids = _.filter(taxes, t => t in this.pos.taxes_by_id);
            result.is_non_zero_vat_taxes_ids = taxes;
            result.is_program_reward = this.is_program_reward;
            result.program_id = this.program_id;
            result.coupon_id = this.coupon_id;
//            console.log('------Orderline-----result---', result)
//            console.log('------Orderline-----this---', this.is_program_reward, this.program_id, this.coupon_id)
            return result;
        },
     });
});
