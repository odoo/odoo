odoo.define('pos_discount.models', function (require) {
  "use strict";

  var models = require('point_of_sale.models');

  var existing_models = models.PosModel.prototype.models;
  var product_index = _.findIndex(existing_models, function (model) {
      return model.model === "product.product";
  });
  var product_model = existing_models[product_index];

  models.load_models([{
    model:  product_model.model,
    fields: product_model.fields,
    order:  product_model.order,
    domain: function(self) {return [['id', '=', self.config.discount_product_id[0]]];},
    context: product_model.context,
    loaded: product_model.loaded,
  }]);

  models.Orderline = models.Orderline.extend({
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
      const is_tips_product = () => this.pos.config.tip_product_id && this.product.id === this.pos.config.tip_product_id[0];
      return !this.is_program_reward && !this.gift_card_id && !is_tips_product();
    }
  });

});
