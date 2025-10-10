import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";

export class orderDetailsDialog extends Component {
    static template = "point_of_sale.orderDetailsDialog";
    static components = { Dialog };
    static props = {
        order: { type: Object },
        close: { type: Function },
    };
    setup() {
        this.pos = usePos();
    }
    get title() {
        return _t("Order ") + this.props.order.tracking_number + _t(" Detail");
    }
    editPayment() {
        this.props.close();
        this.pos.orderDetails(this.props.order);
    }
}
