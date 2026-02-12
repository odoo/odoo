import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

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
}
