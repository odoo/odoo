/** @odoo-module */

import { Component } from "@odoo/owl";

export class IncrementCounter extends Component {
    static template = "pos_self_order.IncrementCounter";
    static props = ["value", "onClick"];
}
