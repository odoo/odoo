odoo.define('pos_discount.models', function (require) {
  "use strict";

  const { Orderline } = require('point_of_sale.models');
  const Registries = require('point_of_sale.Registries');

  const PosDiscountOrderline = (Orderline) => class PosDiscountOrderline extends Orderline {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
      const isTipsProduct = this.pos.config.tip_product_id && this.product.id === this.pos.config.tip_product_id[0];
      return !this.reward_id && !isTipsProduct;
    }
  }
  Registries.Model.extend(Orderline, PosDiscountOrderline);

});
