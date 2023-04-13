/** @odoo-module */

import { Component } from "@odoo/owl";

export class MainButton extends Component {
    static template = "pos_self_order.MainButton";
    static props = { slots: Object, onClick: Function };
}
