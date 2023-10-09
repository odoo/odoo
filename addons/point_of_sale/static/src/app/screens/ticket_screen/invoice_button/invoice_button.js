/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useRef } from "@odoo/owl";

export class InvoiceButton extends Component {
    static template = "point_of_sale.InvoiceButton";

    setup() {
        this.pos = usePos();
        this.invoiceButton = useRef("invoice-button");
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.report = useService("report");
    }
    get isAlreadyInvoiced() {
        if (!this.props.order) {
            return false;
        }
        return Boolean(this.props.order.account_move);
    }
    get commandName() {
        if (!this.props.order) {
            return _t("Invoice");
        } else {
            return this.isAlreadyInvoiced ? _t("Reprint Invoice") : _t("Invoice");
        }
    }
    async _downloadInvoice(orderId) {
        try {
            const [orderWithInvoice] = await this.orm.read(
                "pos.order",
                [orderId],
                ["account_move"],
                { load: false }
            );
            if (orderWithInvoice?.account_move) {
                await this.report.doAction("account.account_invoices", [
                    orderWithInvoice.account_move,
                ]);
            }
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                // NOTE: error here is most probably undefined
                this.popup.add(ErrorPopup, {
                    title: _t("Network Error"),
                    body: _t("Unable to download invoice."),
                });
            }
        }
    }
    async onWillInvoiceOrder(order) {
        return true;
    }
    async _invoiceOrder() {
        const order = this.props.order;
        if (!order) {
            return;
        }

        const orderId = order.backendId;

        // Part 0. If already invoiced, print the invoice.
        if (this.isAlreadyInvoiced) {
            await this._downloadInvoice(orderId);
            return;
        }

        // Part 1: Handle missing partner.
        // Write to pos.order the selected partner.
        if (!order.get_partner()) {
            const { confirmed: confirmedPopup } = await this.popup.add(ConfirmPopup, {
                title: _t("Need customer to invoice"),
                body: _t("Do you want to open the customer list to select customer?"),
            });
            if (!confirmedPopup) {
                return;
            }

            const { confirmed: confirmedTempScreen, payload: newPartner } =
                await this.pos.showTempScreen("PartnerListScreen");
            if (!confirmedTempScreen) {
                return;
            }

            await this.orm.write("pos.order", [orderId], { partner_id: newPartner.id });
        }

        const confirmed = await this.onWillInvoiceOrder(order);
        if (!confirmed) {
            return;
        }

        // Part 2: Invoice the order.
        // FIXME POSREF timeout
        await this.orm.silent.call("pos.order", "action_pos_order_invoice", [orderId]);

        // Part 3: Download invoice.
        await this._downloadInvoice(orderId);
        this.props.onInvoiceOrder(orderId);
    }
    async click() {
        try {
            this.invoiceButton.el.style.pointerEvents = "none";
            await this._invoiceOrder();
        } finally {
            this.invoiceButton.el.style.pointerEvents = "auto";
        }
    }
}
