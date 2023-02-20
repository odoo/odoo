/* @odoo-module */

import { Component } from "@odoo/owl";

export class ImStatus extends Component {
    static props = ["persona", "className?"];
    static template = "mail.im_status";
    static defaultProps = { className: "" };
}
