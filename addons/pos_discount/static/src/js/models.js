/* @odoo-modules */

import { Orderline } from "@point_of_sale/js/models";
import Registries from "@point_of_sale/js/Registries";

const PosDiscountOrderline = (Orderline) =>
  class PosDiscountOrderline extends Orderline {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
      return !(this.pos.config.tip_product_id && this.product.id === this.pos.config.tip_product_id[0]);
    }
  };

Registries.Model.extend(Orderline, PosDiscountOrderline);
