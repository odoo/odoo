import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

const STATEMAP = {
    draft: _t("New"),
    paid: _t("Paid"),
    done: _t("Posted"),
    cancel: _t("Cancelled"),
};
const COLORMAP = { draft: 2, paid: 4, done: 10, cancel: 9 };

export class OrderDetailsDialog extends Component {
    static components = { Dialog, BadgeTag };
    static template = "point_of_sale.OrderDetailsDialog";
    static props = {
        order: { type: Object },
        editPayment: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.sources = { pos: _t("Point of Sale") };
        this.order = this.props.order;
        this.pos = usePos();
        this.orderDetails = [
            {
                title: _t("Order Info"),
                subtitle: formatDateTime(this.order.date_order),
                icon: "fa-bookmark",
                fields: this.getOrderFields(),
                buttons: [
                    {
                        label: STATEMAP[this.order.state],
                        visible: true,
                        colorIndex: COLORMAP[this.order.state],
                    },
                ],
            },
        ];
        if (this.order.payment_ids.length) {
            const orderCurrecy = this.order.currency_id;
            this.orderDetails.push({
                title: _t("Payment Info"),
                subtitle: formatCurrency(this.order.amount_total, orderCurrecy),
                icon: "fa-credit-card",
                buttons: [
                    {
                        label: _t("Edit Payment"),
                        action: this.props.editPayment,
                        visible: this.pos.canEditPayment(this.order),
                        color: "primary",
                    },
                ],
                table: {
                    headers: [_t("Payment Date"), _t("Mode"), _t("Amount")],
                    rows: (this.order.payment_ids || []).map((p) => ({
                        [_t("Payment Date")]: formatDateTime(p.payment_date) || "",
                        [_t("Mode")]: p.payment_method_id?.name || "",
                        [_t("Amount")]: p.amount ? formatCurrency(p.amount, orderCurrecy) : "",
                    })),
                },
            });
        }
    }

    get title() {
        return _t("Order Details: ") + this.order.tracking_number;
    }

    getOrderFields() {
        return [
            { label: _t("Session"), value: this.order.session_id.name },
            { label: _t("Origin"), value: this.sources[this.order.source] },
            { label: _t("Order Reference"), value: this.order.name },
            { label: _t("Receipt Number"), value: this.order.pos_reference },
            { label: _t("Served By"), value: this.order.user_id?.name },
            { label: _t("Customer"), value: this.order.partner_id?.name },
        ];
    }
}
