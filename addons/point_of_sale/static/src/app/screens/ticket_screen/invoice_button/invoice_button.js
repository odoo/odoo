/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PartnerList } from "../../partner_list/partner_list";

export class InvoiceButton extends Component {
    static template = "point_of_sale.InvoiceButton";
    static props = {
        order: Object,
        onInvoiceOrder: Function,
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.report = useService("report");
        this.lock = false;
    }
    get isAlreadyInvoiced() {
        if (!this.props.order) {
            return false;
        }
        return Boolean(this.props.order.raw.account_move);
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
            const orderWithInvoice = await this.pos.data.read("pos.order", [orderId], [], {
                load: false,
            });
            const order = orderWithInvoice[0];
            const accountMove = order.raw.account_move;
            if (accountMove) {
                await this.report.doAction("account.account_invoices", [accountMove]);
            }
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                // NOTE: error here is most probably undefined
                this.dialog.add(AlertDialog, {
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

        const orderId = order.id;
        // Part 0. If already invoiced, print the invoice.
        if (this.isAlreadyInvoiced) {
            await this._downloadInvoice(orderId);
            this.props.onInvoiceOrder(orderId);
            return;
        }

        // Part 1: Handle missing partner.
        // Write to pos.order the selected partner.
        if (!order.get_partner()) {
            const _confirmed = await ask(this.dialog, {
                title: _t("Need customer to invoice"),
                body: _t("Do you want to open the customer list to select customer?"),
            });
            if (!_confirmed) {
                return;
            }
            const newPartner = await makeAwaitable(this.dialog, PartnerList);
            if (!newPartner) {
                return;
            }

            await this.pos.data.ormWrite("pos.order", [orderId], { partner_id: newPartner.id });
        }

        const confirmed = await this.onWillInvoiceOrder(order);
        if (!confirmed) {
            return;
        }

        // Part 2: Invoice the order.
        // FIXME POSREF timeout
        await this.pos.data.silentCall("pos.order", "action_pos_order_invoice", [orderId]);

        // Part 3: Download invoice.
        await this._downloadInvoice(orderId);
        this.props.onInvoiceOrder(orderId);
    }
    async click() {
        if (this.lock) {
            return;
        }

        this.lock = true;
        try {
            await this._invoiceOrder();
        } finally {
            this.lock = false;
        }
    }
}
