/** @odoo-module */

import { Component } from "@odoo/owl";

// Previously UsernameWidget
export class CashierName extends Component {
    static template = "CashierName";

    get username() {
        const { name } = this.env.pos.get_cashier();
        return name ? name : "";
    }
    get avatar() {
        const user_id = this.env.pos.get_cashier_user_id();
        const id = user_id ? user_id : -1;
        return `/web/image/res.users/${id}/avatar_128`;
    }
    get cssClass() {
        return { "not-clickable": true };
    }
}
