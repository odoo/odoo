odoo.define('pos_sale.models', function (require) {
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
  domain: function(self) {return [['id', '=', self.config.down_payment_product_id[0]]];},
  context: product_model.context,
  loaded: product_model.loaded,
}]);

models.load_fields("product.product", ["invoice_policy", "type"]);

var super_order_line_model = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
  initialize: function (attributes, options) {
      super_order_line_model.initialize.apply(this, arguments);
      // It is possible that this orderline is initialized using `init_from_JSON`,
      // meaning, it is loaded from localStorage or from export_for_ui. This means
      // that some fields has already been assigned. Therefore, we only set the options
      // when the original value is falsy.
      this.sale_order_origin_id = this.sale_order_origin_id || options.sale_order_origin_id;
      this.sale_order_line_id = this.sale_order_line_id || options.sale_order_line_id;
      this.down_payment_details = this.down_payment_details || options.down_payment_details;
      this.customerNote = this.customerNote || options.customer_note;
  },
  init_from_JSON: function (json) {
      super_order_line_model.init_from_JSON.apply(this, arguments);
      this.sale_order_origin_id = json.sale_order_origin_id;
      this.sale_order_line_id = json.sale_order_line_id;
      this.down_payment_details = json.down_payment_details && JSON.parse(json.down_payment_details);
  },
  export_as_JSON: function () {
      const json = super_order_line_model.export_as_JSON.apply(this, arguments);
      json.sale_order_origin_id = this.sale_order_origin_id;
      json.sale_order_line_id = this.sale_order_line_id;
      json.down_payment_details = this.down_payment_details && JSON.stringify(this.down_payment_details);
      return json;
  },
  get_sale_order: function(){
      if(this.sale_order_origin_id) {
        let value = {
            'name': this.sale_order_origin_id.name,
            'details': this.down_payment_details || false
        }

        return value;
      }
      return false;
  },
  export_for_printing: function() {
    var json = super_order_line_model.export_for_printing.apply(this,arguments);
    json.down_payment_details =  this.down_payment_details;
    if (this.sale_order_origin_id) {
        json.so_reference = this.sale_order_origin_id.name;
    }
    return json;
  },
  /**
   * Set quantity based on the give sale order line.
   * @param {'sale.order.line'} saleOrderLine
   */
  setQuantityFromSOL: function(saleOrderLine) {
      if (this.product.type === 'service') {
        this.set_quantity(saleOrderLine.qty_to_invoice);
      } else {
        this.set_quantity(saleOrderLine.product_uom_qty - Math.max(saleOrderLine.qty_delivered, saleOrderLine.qty_invoiced));
      }
  }
});

});
