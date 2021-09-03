odoo.define("pos_gift_card.GiftCardPopup", function (require) {
  "use strict";

  const { useState } = owl.hooks;
  const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
  const { useBarcodeReader } = require("point_of_sale.custom_hooks");
  const Registries = require("point_of_sale.Registries");

  class GiftCardPopup extends AbstractAwaitablePopup {
    constructor() {
      super(...arguments);

      this.confirmFunctions = {
        'create_set': this.generateBarcode.bind(this),
        'scan_set': this.scanAndUseGiftCard.bind(this),
        'scan_use': this.scanAndUseGiftCard.bind(this),
        'pay': this.payWithGiftCard.bind(this),
        'showAmount': this.showRemainingAmount.bind(this)
      };

      this.state = useState({
        giftCardConfig: this.env.pos.config.gift_card_settings,
        showMenu: true,
        error: '',
        command: '',
        amountToSet: 0,
        giftCardBarcode: "",
        remainingAmount: 0,
      });
      useBarcodeReader(
        {
          gift_card: this._onGiftScan,
        },
        true
      );
    }

    clickConfirm() {
        this.confirmFunctions[this.state.command]();
    }

    _onGiftScan(code) {
      this.state.giftCardBarcode = code.base_code;
    }

    switchToBarcode() {
      this.state.command = this.state.giftCardConfig;
      this.state.showMenu = false;
    }

    backToMenu() {
        this.state.showMenu = true;
        this.state.command = '';
        this.state.amountToSet = 0;
        this.state.giftCardBarcode = '';
        this.state.error = '';
        this.state.remainingAmount = 0;
    }

    switchToPay() {
      this.state.showMenu = false;
      this.state.command = 'pay';
    }

    switchToShowGiftCardDetails() {
      this.state.showMenu = false;
      this.state.command = 'showAmount';
    }

    addGiftCardProduct(giftCard) {
      let gift =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];
      this.env.pos.get_order().add_product(gift, {
        price: this.state.amountToSet,
        quantity: 1,
        merge: false,
        generated_gift_card_ids: giftCard ? giftCard[0].id : false,
      });
    }

    async getGiftCard() {
      let barcode = this.state.giftCardBarcode.trim();
      if (barcode == "") return;
      let giftCard = await this.rpc({
        model: "gift.card",
        method: "search_read",
        args: [[["code", "=", barcode]]],
        fields: ["code", "initial_amount", "balance"],
      });
      return giftCard.length? giftCard : false;
    }

    async checkGiftCardError(giftCard) {
        if (!giftCard) {
            this.state.error = "Invalid gift card code";
            return true;
        }
        let lineUsed = await this.isGiftCardAlreadyUsed();
        if(lineUsed) {
            this.state.error = "Gift card already used";
            return true;
        }
        return false;
    }

    async scanAndUseGiftCard() {
      let giftCard = await this.getGiftCard();

      if(await this.checkGiftCardError(giftCard)) return;

      if (this.state.giftCardConfig === "scan_use")
        this.state.amountToSet = giftCard.initial_amount;

      this.addGiftCardProduct(giftCard);
      this.cancel();
    }

    async generateBarcode() {
      this.addGiftCardProduct(false);
      this.confirm();
    }

    async isGiftCardAlreadyUsed() {
      let order = this.env.pos.get_order();
      let giftProduct =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];

      let currentGiftCard = await this.getGiftCard();
      let currentGiftCardId = currentGiftCard && currentGiftCard[0].id;
      for (let line of order.orderlines.models) {
        if (line.product.id === giftProduct.id) {
          if (line.gift_card_id === currentGiftCardId) return line;
        }
      }
      return false;
    }

    getPriceToRemove(giftCard) {
      let currentOrder = this.env.pos.get_order();
      return currentOrder.get_total_with_tax() > giftCard[0].balance
        ? -giftCard[0].balance
        : -currentOrder.get_total_with_tax();
    }

    async payWithGiftCard() {
      let giftCard = await this.getGiftCard();
      if(await this.checkGiftCardError(giftCard)) return;

      let gift =
        this.env.pos.db.product_by_id[
          this.env.pos.config.gift_card_product_id[0]
        ];

      let currentOrder = this.env.pos.get_order();
      let lineUsed = await this.isGiftCardAlreadyUsed();
      if (lineUsed) currentOrder.remove_orderline(lineUsed);

      currentOrder.add_product(gift, {
        price: this.getPriceToRemove(giftCard),
        quantity: 1,
        merge: false,
        gift_card_id: giftCard[0].id,
      });

      this.cancel();
    }

    async showRemainingAmount() {
      let giftCard = await this.getGiftCard();
      if(await this.checkGiftCardError(giftCard)) return;

      this.state.remainingAmount = giftCard[0].balance;
    }
  }
  GiftCardPopup.template = "GiftCardPopup";

  Registries.Component.add(GiftCardPopup);

  return GiftCardPopup;
});
