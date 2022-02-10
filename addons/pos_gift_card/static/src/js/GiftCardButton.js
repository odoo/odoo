odoo.define("pos_gift_card.GiftCardButton", function (require) {
  "use strict";

  const PosComponent = require("point_of_sale.PosComponent");
  const ProductScreen = require("point_of_sale.ProductScreen");
  const { useListener } = require("@web/core/utils/hooks");
  const Registries = require("point_of_sale.Registries");

  class GiftCardButton extends PosComponent {
    setup() {
      super.setup();
      useListener("click", this.onClick);
    }
    async onClick() {
      this.showPopup("GiftCardPopup", {});
    }
  }
  GiftCardButton.template = "GiftCardButton";

  ProductScreen.addControlButton({
    component: GiftCardButton,
    condition: function () {
      return this.env.pos.config.use_gift_card;
    },
  });

  Registries.Component.add(GiftCardButton);

  return GiftCardButton;
});
