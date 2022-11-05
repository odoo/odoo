/** @odoo-module */

import { Component } from "@odoo/owl";

export class ThreadIcon extends Component {
    static template = "mail.thread_icon";
    static props = ["thread", "className?"];
}
