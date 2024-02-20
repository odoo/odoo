/** @odoo-module */

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.printer = useService("printer");
        this.clickPrintBill = useAsyncLockedMethod(this.clickPrintBill);
    },
    async clickPrintBill() {
        // Need to await to have the result in case of automatic skip screen.
        (await this.printer.print(OrderReceipt, {
            data: this.pos.get_order().export_for_printing(),
            formatCurrency: this.env.utils.formatCurrency,
        })) || this.dialog.add(BillScreen);
    },
    clickTableGuests() {
        this.dialog.add(NumberPopup, {
            startingValue: this.currentOrder?.getCustomerCount() || 0,
            cheap: true,
            title: _t("Guests?"),
            isInputSelected: true,
            getPayload: (inputNumber) => {
                const guestCount = parseInt(inputNumber, 10) || 0;
                if (guestCount == 0 && this.currentOrder.orderlines.length === 0) {
                    this.pos.removeOrder(this.currentOrder);
                    this.pos.showScreen("FloorScreen");
                }
                this.currentOrder.setCustomerCount(guestCount);
            },
        });
    },
    clickTransferOrder() {
        this.pos.orderToTransfer = this.pos.selectedOrder;
        this.pos.get_order().setBooked(true);
        this.pos.showScreen("FloorScreen");
    },
    async sendOrderInPreparatonByCateg() {
        const lineOldSkipState = {};
        const selectable = this.pos.models["pos.category"].map((c) => {
            return {
                id: c.id,
                label: c.name,
                isSelected: false,
                item: c,
            };
        });
        const category = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select a category to send in preparation"),
            list: selectable,
        });

        if (!category) {
            return;
        }

        for (const line of this.currentOrder.orderlines) {
            const lineCategids = line.product.pos_categ_ids.map((c) => c.id);
            lineOldSkipState[line.id] = line.skipChange;

            if (!lineCategids.includes(category.id)) {
                line.skipChange = true;
            }
        }
        this.pos.db.save_unpaid_order(this.currentOrder);
        await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
        for (const line of this.currentOrder.orderlines) {
            line.skipChange = lineOldSkipState[line.id];
        }
    },
});
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SelectPartnerButton,
    },
});
