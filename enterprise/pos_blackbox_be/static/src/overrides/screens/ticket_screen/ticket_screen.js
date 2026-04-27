import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.numberBuffer = useService("number_buffer");
        this.notification = useService("notification");
    },
    async print(order) {
        if (this.pos.useBlackBoxBe()) {
            await this.dialog.add(AlertDialog, {
                title: _t("Fiscal Data Module Restriction"),
                body: _t(
                    "You are not allowed to reprint a ticket when using the fiscal data module."
                ),
            });
            return;
        }

        await super.print(order);
    },
    _onUpdateSelectedOrderline({ key, buffer }) {
        /**
         * Prevent refunding work in/out lines.
         */
        if (this.pos.useBlackBoxBe()) {
            const order = this.getSelectedOrder();
            if (!order) {
                return this.numberBuffer.reset();
            }

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
            if (!orderline) {
                return this.numberBuffer.reset();
            }
            if (
                [this.pos.config.work_in_product.id, this.pos.config.work_out_product.id].includes(
                    orderline.product_id.id
                )
            ) {
                this.notification.add(_t("Refunding work in/out product is not allowed."));
                return;
            }
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },
});
