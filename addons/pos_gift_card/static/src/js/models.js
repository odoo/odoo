odoo.define("pos_gift_card.gift_card", function (require) {
  "use strict";

  const models = require("point_of_sale.models");

  models.load_fields("pos.order.line", "generated_gift_card_ids");
  models.load_fields("pos.order.line", "redeem_pos_order_line_ids");

    // Load the products used for creating program reward lines.
    var existing_models = models.PosModel.prototype.models;
    var product_index = _.findIndex(existing_models, function (model) {
        return model.model === 'product.product';
    });
    var product_model = existing_models[product_index];

  models.load_models([
    {
        model: product_model.model,
        fields: product_model.fields,
        order: product_model.order,
        domain: function (self) {
            return [['id', '=', self.config.gift_card_product_id[0]]];
        },
        context: product_model.context,
        loaded: product_model.loaded,
    },
  ]);

  var _order_super = models.Order.prototype;
  models.Order = models.Order.extend({
    //@override
    set_orderline_options: function (orderline, options) {
      _order_super.set_orderline_options.apply(this, [orderline, options]);
      if (options && options.generated_gift_card_ids) {
        orderline.generated_gift_card_ids = [options.generated_gift_card_ids];
      }
      if (options && options.gift_card_id) {
        orderline.gift_card_id = options.gift_card_id;
      }
    },
    //@override
    wait_for_push_order: function () {
        if(this.pos.config.use_gift_card) {
            let giftProduct = this.pos.db.product_by_id[this.pos.config.gift_card_product_id[0]];
            for (let line of this.orderlines.models) {
                if(line.product.id === giftProduct.id)
                    return true;
            }
        }
        return _order_super.wait_for_push_order.apply(this, arguments);
    },
    //@override
    _reduce_total_discount_callback: function(sum, orderLine) {
        if (this.pos.config.gift_card_product_id[0] === orderLine.product.id) {
            return sum;
        }
        return _order_super._reduce_total_discount_callback.apply(this, arguments);
    },

  });

  var _super_orderline = models.Orderline;
  models.Orderline = models.Orderline.extend({
    export_as_JSON: function () {
      var json = _super_orderline.prototype.export_as_JSON.apply(
        this,
        arguments
      );
      json.generated_gift_card_ids = this.generated_gift_card_ids;
      json.gift_card_id = this.gift_card_id;
      return json;
    },
    init_from_JSON: function (json) {
      _super_orderline.prototype.init_from_JSON.apply(this, arguments);
      this.generated_gift_card_ids = json.generated_gift_card_ids;
      this.gift_card_id = json.gift_card_id;
    },
  });

  var _posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        print_gift_pdf: function (giftCardIds) {
            this.do_action('pos_gift_card.gift_card_report_pdf', {
                additional_context: {
                    active_ids: [giftCardIds],
                },
            })
        }
    });
});
