odoo.define("pos_gift_card.gift_card", function (require) {
  "use strict";

  const { Order, Orderline } = require("point_of_sale.models");
  const Registries = require('point_of_sale.Registries');


  const PosGiftCardOrder = (Order) => class PosGiftCardOrder extends Order {
    //@override
    _reduce_total_discount_callback(sum, orderLine) {
        if (this.pos.config.gift_card_product_id[0] === orderLine.product.id) {
            return sum;
        }
        return super._reduce_total_discount_callback(...arguments);
    }
    //@override
    set_orderline_options(orderline, options) {
      super.set_orderline_options(...arguments);
      if (options && options.generated_gift_card_ids) {
        orderline.generated_gift_card_ids = [options.generated_gift_card_ids];
      }
      if (options && options.gift_card_id) {
        orderline.gift_card_id = options.gift_card_id;
      }
    }
    //override
    wait_for_push_order() {
        if(this.pos.config.use_gift_card) {
            let giftProduct = this.pos.db.product_by_id[this.pos.config.gift_card_product_id[0]];
            for (let line of this.orderlines) {
                if(line.product.id === giftProduct.id)
                    return true;
            }
        }
        return super.wait_for_push_order(...arguments);
    }
  }
  Registries.Model.extend(Order, PosGiftCardOrder);


  const PosGiftCardOrderline = (Orderline) => class PosGiftCardOrderline extends Orderline {
    export_as_JSON() {
      var json = super.export_as_JSON(...arguments);
      json.generated_gift_card_ids = this.generated_gift_card_ids;
      json.gift_card_id = this.gift_card_id;
      return json;
    }
    init_from_JSON(json) {
      super.init_from_JSON(...arguments);
      this.generated_gift_card_ids = json.generated_gift_card_ids;
      this.gift_card_id = json.gift_card_id;
    }
  }
  Registries.Model.extend(Orderline, PosGiftCardOrderline);
});
