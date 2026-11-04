import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

// Previously UsernameWidget
export class CashierName extends Component {
    static template = "point_of_sale.CashierName";
    static props = {};

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
    get username() {
        const cashier = this.pos.get_cashier();
        return cashier ? cashier.name : "";
    }
    get avatar() {
        const user_id = this.pos.get_cashier_user_id();
        const id = user_id ? user_id : -1;
        return `/web/image/res.users/${id}/avatar_128`;
    }
    get cssClass() {
        return { "not-clickable pe-none": true };
    }
}
