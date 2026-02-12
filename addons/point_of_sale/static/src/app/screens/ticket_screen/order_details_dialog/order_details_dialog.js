import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { useService } from "@web/core/utils/hooks";

const STATES = {
    draft: { label: _t("New"), color: 2 },
    paid: { label: _t("Paid"), color: 4 },
    done: { label: _t("Posted"), color: 10 },
    cancel: { label: _t("Cancelled"), color: 9 },
};

export class OrderDetailsDialog extends Component {
    static components = { Dialog, BadgeTag };
    static template = "point_of_sale.OrderDetailsDialog";
    static props = {
        order: { type: Object },
        editPayment: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.pos = usePos();
        this.states = STATES;
        this.ui = useService("ui");
    }

    get title() {
        return _t("Order Details: ") + this.props.order.tracking_number;
    }

    formatDateTime(dt) {
        return formatDateTime(dt);
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.props.order.currency_id);
    }

    getOrderFields() {
        const order = this.props.order;
        return [
            {
                id: "session",
                label: _t("Session"),
                value: order.session_id?.name,
                condition: !!order.session_id?.name,
            },
            {
                id: "origin",
                label: _t("Origin"),
                value: _t("Point of Sale"),
                condition: order.source === "pos",
            },
            {
                id: "order_reference",
                label: _t("Order Reference"),
                value: order.name,
                condition: !!order.name,
            },
            {
                id: "receipt_number",
                label: _t("Receipt Number"),
                value: order.pos_reference,
                condition: !!order.pos_reference,
            },
            {
                id: "served_by",
                label: _t("Served By"),
                value: order.user_id?.name,
                condition: !!order.user_id?.name,
            },
            {
                id: "customer",
                label: _t("Customer"),
                value: order.partner_id?.name,
                condition: !!order.partner_id?.name,
            },
            {
                id: "order_time",
                label: _t("Order Time"),
                value: this.formatDateTime(order.date_order),
                condition: !!order.date_order,
            },
        ];
    }
}
