/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { onWillUnmount } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
  setup() {
    super.setup(...arguments);
    onWillUnmount(() => {
      this.env.services.barcode_reader.bypassQR = false;
    });
  },

  async onMounted() {
    await super.onMounted(...arguments);
    const alipay_line = this.pos.getPendingPaymentLine("alipay");
    if (alipay_line) {
      this.env.services.barcode_reader.bypassQR = true;
    }
  },
});
