import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
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
        this.invoiceService = useService("account_move");
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
            const orders = await this.pos.data.loadServerOrders([["id", "=", orderId]]);
            const order = orders[0];
            const accountMoveId = order.raw.account_move;
            if (accountMoveId) {
                await this.invoiceService.downloadPdf(accountMoveId);
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
    async onWillInvoiceOrder(order, partner) {
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
        let partner = order.getPartner();
        if (!partner) {
            const _confirmed = await ask(this.dialog, {
                title: _t("Need customer to invoice"),
                body: _t("Do you want to open the customer list to select customer?"),
            });
            if (!_confirmed) {
                return;
            }
            partner = await makeAwaitable(this.dialog, PartnerList);
            if (!partner) {
                return;
            }

            await this.pos.data.ormWrite("pos.order", [orderId], { partner_id: partner.id });
        }

        const confirmed = await this.onWillInvoiceOrder(order, partner);
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
