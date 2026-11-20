import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/app/components/popups/company_state_dialog/company_state_dialog";

patch(InvoiceButton.prototype, {
    async click() {
        await this.pos.data.read("res.company", [this.pos.company.id]);
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return await super.click();
    },
    async _invoiceOrder() {
        const order = this.props.order;
        if (!order?.isL10nInB2CInvoiced) {
            return await super._invoiceOrder(...arguments);
        }
        // The B2C invoice is replaced by an invoice on the name of the selected customer.
        const confirmed = await ask(this.dialog, {
            title: _t("Invoice to a customer"),
            body: _t(
                "This order already has a B2C invoice. It will be cancelled by a credit note and the order will be invoiced to the customer you select."
            ),
        });
        if (!confirmed) {
            return;
        }
        const partner = await makeAwaitable(this.dialog, PartnerList, { order });
        if (!partner || partner.id === order.partner_id?.id) {
            return;
        }
        const downloadAction = await this.pos.data.call(
            "pos.order",
            "action_l10n_in_invoice_to_customer",
            [order.id, partner.id]
        );
        await this.pos.action.doAction(downloadAction);
        await this.pos.data.loadServerOrders([["id", "=", order.id]]);
        this.props.onInvoiceOrder(order.id);
    },
});
