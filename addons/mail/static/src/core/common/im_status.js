/* @odoo-module */

import { Component } from "@odoo/owl";

export class ImStatus extends Component {
    static props = ["persona", "className?", "style?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "" };
}
