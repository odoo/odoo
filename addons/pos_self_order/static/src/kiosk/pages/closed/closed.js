/** @odoo-module */

import { Component } from "@odoo/owl";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class Closed extends Component {
    static template = "pos_self_order.Closed";
    static components = { KioskTemplate };
}
