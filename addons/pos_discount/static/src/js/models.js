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
    loaded: function(self, products){
        if (products.length) {
            products[0].taxes_id = [];
        }
        product_model.loaded(self, products);
    }
  }]);

});
