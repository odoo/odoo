/* @odoo-module */

import { Component } from "@odoo/owl";

export class ImStatus extends Component {
    static props = ["persona", "className?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "" };
}
