import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.alert = useService("alert");
        this.printer = useService("printer");
        this.clickPrintBill = useAsyncLockedMethod(this.clickPrintBill);
    },
    async clickPrintBill() {
        // Need to await to have the result in case of automatic skip screen.
        (await this.printer.print(OrderReceipt, {
            data: this.pos.orderExportForPrinting(this.pos.get_order()),
            formatCurrency: this.env.utils.formatCurrency,
        })) || this.dialog.add(BillScreen);
    },
    clickTableGuests() {
        this.dialog.add(NumberPopup, {
            startingValue: this.currentOrder?.getCustomerCount() || 0,
            title: _t("Guests?"),
            feedback: (buffer) => {
                const value = this.env.utils.formatCurrency(
                    this.currentOrder.amountPerGuest(parseInt(buffer, 10) || 0)
                );
                return value ? `${value} / ${_t("Guest")}` : "";
            },
            getPayload: (inputNumber) => {
                const guestCount = parseInt(inputNumber, 10) || 0;
                if (guestCount == 0 && this.currentOrder.lines.length === 0) {
                    this.pos.removeOrder(this.currentOrder);
                    this.pos.showScreen("FloorScreen");
                }
                this.currentOrder.setCustomerCount(guestCount);
                this.pos.addPendingOrder([this.currentOrder.id]);
            },
        });
    },
    clickTransferOrder() {
        this.pos.orderToTransferUuid = this.pos.get_order().uuid;
        this.pos.get_order().setBooked(true);
        this.pos.showScreen("FloorScreen");
    },
    clickTakeAway() {
        const isTakeAway = !this.currentOrder.takeaway;
        const defaultFp = this.pos.config?.default_fiscal_position_id ?? false;
        const takeawayFp = this.pos.config.takeaway_fp_id;

        this.currentOrder.takeaway = isTakeAway;
        this.currentOrder.update({ fiscal_position_id: isTakeAway ? takeawayFp : defaultFp });
    },
});
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SelectPartnerButton,
    },
});
