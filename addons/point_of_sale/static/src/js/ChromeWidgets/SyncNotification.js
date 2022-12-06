/** @odoo-module */

const PosComponent = require("point_of_sale.PosComponent");
const Registries = require("point_of_sale.Registries");

export class SyncNotification extends PosComponent {
    onClick() {
        this.env.pos.push_orders(null, { show_error: true });
    }
}
SyncNotification.template = "point_of_sale.SyncNotification";

Registries.Component.add(SyncNotification);
