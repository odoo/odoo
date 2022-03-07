odoo.define("pos_gift_card.GiftCardPopup", function (require) {
  "use strict";

  const { useState, useRef } = owl.hooks;
  const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
  const Registries = require("point_of_sale.Registries");

  class GiftCardPopup extends AbstractAwaitablePopup {
    constructor() {
      super(...arguments);
      this.state = useState({
        giftCardConfig: this.env.pos.config.gift_card_settings,
        showBarcodeGeneration: false,
        showNewGiftCardMenu: false,
        showUseGiftCardMenu: false,
        showGiftCardDetails: false,
        amountToSet: 0,
        giftCardBarcode: "",
      });
    }

    switchBarcodeView() {
      this.state.showBarcodeGeneration = !this.state.showBarcodeGeneration;
      if (this.state.showUseGiftCardMenu)
        this.state.showUseGiftCardMenu = false;
      if (this.state.showGiftCardDetails)
        this.state.showGiftCardDetails = false;
    }

    switchToUseGiftCardMenu() {
      this.switchBarcodeView();
      this.state.showUseGiftCardMenu = true;
    }

    switchToShowGiftCardDetails() {
      this.switchBarcodeView();
      this.state.showGiftCardDetails = true;
    }

    async addGiftCardProduct(giftCard) {
      let gift =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];

      let can_be_sold = true;
      if (giftCard) {
        can_be_sold = !(giftCard.buy_pos_order_line_id || giftCard.buy_line_id);
      }

      if (can_be_sold) {
        this.env.pos.get_order().add_product(gift, {
          price: this.state.amountToSet,
          quantity: 1,
          merge: false,
          generated_gift_card_ids: giftCard ? giftCard.id : false,
          extras: { price_manually_set: true },
        });
      } else {
        await this.showPopup('ErrorPopup', {
          'title': this.env._t('This gift card has already been sold'),
          'body': this.env._t('You cannot sell a gift card that has already been sold'),
        });
      }
    }

    async getGiftCard() {
      if (this.state.giftCardBarcode == "") return;

      let giftCard = await this.rpc({
          model: "gift.card",
          method: "search_read",
          args: [[["code", "=", this.state.giftCardBarcode]]],
        });
        if (giftCard.length) {
          giftCard = giftCard[0];
        } else {
          return false;
        }

      return giftCard;
    }

    async scanAndUseGiftCard() {
      let giftCard = await this.getGiftCard();
      if (!giftCard) return;

      if (this.state.giftCardConfig === "scan_use")
        this.state.amountToSet = giftCard.initial_amount;

      await this.addGiftCardProduct(giftCard);
      this.cancel();
    }

    async generateBarcode() {
      await this.addGiftCardProduct(false);
      this.confirm();
    }

    async isGiftCardAlreadyUsed() {
      let order = this.env.pos.get_order();
      let giftProduct =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];

      for (let line of order.orderlines.models) {
        if (line.product.id === giftProduct.id && line.price < 0) {
          if (line.gift_card_id === await this.getGiftCard().id) return line;
        }
      }
      return false;
    }

    getPriceToRemove(giftCard) {
      let currentOrder = this.env.pos.get_order();
      return currentOrder.get_total_with_tax() > giftCard.balance
        ? -giftCard.balance
        : -currentOrder.get_total_with_tax();
    }

    async payWithGiftCard() {
      let giftCard = await this.getGiftCard();
      if (!giftCard) return;

      let gift =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];

      let currentOrder = this.env.pos.get_order();
      let lineUsed = this.isGiftCardAlreadyUsed()
      if (lineUsed) currentOrder.remove_orderline(lineUsed);

      currentOrder.add_product(gift, {
        price: this.getPriceToRemove(giftCard),
        quantity: 1,
        merge: false,
        gift_card_id: giftCard.id,
      });

      this.cancel();
    }

    async ShowRemainingAmount() {
      let giftCard = await this.getGiftCard();
      if (!giftCard) return;

      this.state.amountToSet = giftCard.balance;
    }
  }
  GiftCardPopup.template = "GiftCardPopup";

  Registries.Component.add(GiftCardPopup);

  return GiftCardPopup;
});
