import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    clickRefund() {
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            this.dialog.add(AlertDialog, {
                title: this._t("POS error"),
                body: this._t("User must be clocked in."),
            });
            return;
        }
        super.clickRefund();
    },
    async clickPrintBill() {
        const order = this.pos.get_order();
        if (this.pos.useBlackBoxBe() && order.get_orderlines().length > 0) {
            this.pos.addPendingOrder([order.id]);
            const result = await this.pos.syncAllOrders({ throw: true });
            if (!result) {
                return;
            }
        }
        await super.clickPrintBill();
    },
    async apply_discount(pc) {
        if (this.pos.useBlackBoxBe()) {
            try {
                const order = this.pos.get_order();
                const lines = order.get_orderlines();
                this.pos.multiple_discount = true;

                await this.pos.pushCorrection(order); //push the correction order

                for (const line of lines) {
                    await this.pos.setDiscountFromUI(line, pc);
                }
                this.pos.addPendingOrder([order.id]);
                await this.pos.syncAllOrders({ throw: true });
            } finally {
                this.pos.multiple_discount = false;
            }
        } else {
            await super.apply_discount(pc);
        }
    },
});
