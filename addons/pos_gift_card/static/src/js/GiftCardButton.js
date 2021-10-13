odoo.define("pos_gift_card.GiftCardButton", function (require) {
  "use strict";

  const PosComponent = require("point_of_sale.PosComponent");
  const { useListener } = require("web.custom_hooks");
  const Registries = require("point_of_sale.Registries");

  class GiftCardButton extends PosComponent {
    constructor() {
      super(...arguments);
      useListener("click", this.onClick);
    }
    async onClick() {
      this.showPopup("GiftCardPopup", {});
    }
  }
  GiftCardButton.template = "GiftCardButton";
  Registries.Component.add(GiftCardButton);

  return GiftCardButton;
});
