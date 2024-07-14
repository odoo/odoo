/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

patch(PartnerLine.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.popup = useService("popup");
    },
    getPartnerLink() {
        return `/web#model=res.partner&id=${this.props.partner.id}`;
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
    async settlePartnerDue(event) {
        if (this.props.selectedPartner == this.props.partner) {
            event.stopPropagation();
        }
        const totalDue = this.props.partner.total_due;
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
        this.trigger("discard"); // make sure the PartnerListScreen resolves and properly closed.
        const newOrder = this.pos.add_new_order();
        const payment = newOrder.add_paymentline(selectedPaymentMethod);
        payment.set_amount(totalDue);
        newOrder.set_partner(this.props.partner);
        this.pos.showScreen("PaymentScreen");
    },
});
