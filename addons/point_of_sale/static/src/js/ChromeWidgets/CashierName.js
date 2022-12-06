/** @odoo-module */

const PosComponent = require("point_of_sale.PosComponent");

// Previously UsernameWidget
export class CashierName extends PosComponent {
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
CashierName.template = "point_of_sale.CashierName";
