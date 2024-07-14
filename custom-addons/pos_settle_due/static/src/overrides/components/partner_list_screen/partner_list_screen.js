/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useService } from "@web/core/utils/hooks";

patch(PartnerListScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
    },
    get isBalanceDisplayed() {
        return true;
    },
    get partnerLink() {
        return `/web#model=res.partner&id=${this.state.editModeProps.partner.id}`;
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
    async settleCustomerDue() {
        const updatedDue = await this.pos.refreshTotalDueOfPartner(
            this.state.editModeProps.partner
        );
        const totalDue = updatedDue
            ? updatedDue[0].total_due
            : this.state.editModeProps.partner.total_due;
        const paymentMethods = this.pos.payment_methods.filter(
            (method) =>
                this.pos.config.payment_method_ids.includes(method.id) && method.type != "pay_later"
        );
        const selectionList = paymentMethods.map((paymentMethod) => ({
            id: paymentMethod.id,
            label: paymentMethod.name,
            item: paymentMethod,
        }));
        const { confirmed, payload: selectedPaymentMethod } = await this.popup.add(SelectionPopup, {
            title: _t("Select the payment method to settle the due"),
            list: selectionList,
        });
        if (!confirmed) {
            return;
        }
        this.state.selectedPartner = this.state.editModeProps.partner;
        this.confirm(); // make sure the PartnerListScreen resolves and properly closed.

        // Reuse an empty order that has no partner or has partner equal to the selected partner.
        let newOrder;
        const emptyOrder = this.pos.orders.find(
            (order) =>
                order.orderlines.length === 0 &&
                order.paymentlines.length === 0 &&
                (!order.partner || order.partner.id === this.state.selectedPartner.id)
        );
        if (emptyOrder) {
            newOrder = emptyOrder;
            // Set the empty order as the current order.
            this.pos.set_order(newOrder);
        } else {
            newOrder = this.pos.add_new_order();
        }
        const payment = newOrder.add_paymentline(selectedPaymentMethod);
        payment.set_amount(totalDue);
        newOrder.set_partner(this.state.selectedPartner);
        this.pos.showScreen("PaymentScreen");
    },
});
