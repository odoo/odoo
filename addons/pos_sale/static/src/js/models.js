odoo.define('pos_sale.models', function (require) {
    "use strict";

var models = require('point_of_sale.models');


var super_order_model = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function (attributes, options) {
        super_order_model.initialize.apply(this, arguments);
        this.sale_order_origin_id = options.sale_order_origin_id;
    },
    export_as_JSON: function () {
        const json = super_order_model.export_as_JSON.apply(this, arguments);
        json.sale_order_origin_id = this.sale_order_origin_id ? this.sale_order_origin_id.id : false;
        return json;
    },
    export_for_printing: function(){
        var json = super_order_model.export_for_printing.apply(this,arguments);
        if (this.sale_order_origin_id) {
            json.so_reference = this.sale_order_origin_id.name;
        }
        return json;
    },
});

var super_order_line_model = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
  initialize: function (attributes, options) {
      super_order_line_model.initialize.apply(this, arguments);
      this.sale_order_origin_id = options.sale_order_origin_id;
  },
  init_from_JSON: function (json) {
      super_order_line_model.init_from_JSON.apply(this, arguments);
      this.sale_order_origin_id = json.sale_order_origin_id;
  },
  export_as_JSON: function () {
      const json = super_order_line_model.export_as_JSON.apply(this, arguments);
      json.sale_order_origin_id = this.sale_order_origin_id ? this.sale_order_origin_id.id : false;
      return json;
  },
  get_sale_order: function(){
      return this.sale_order_origin_id ? this.sale_order_origin_id.name: false;
  },
  export_for_printing: function() {
    var json = super_order_line_model.export_for_printing.apply(this,arguments);
    if (this.sale_order_origin_id) {
        json.so_reference = this.sale_order_origin_id.name;
    }
    return json;
  },
});

});
