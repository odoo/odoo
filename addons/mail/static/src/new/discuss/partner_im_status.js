/* @odoo-module */

import { Component } from "@odoo/owl";

export class PartnerImStatus extends Component {
    static props = ["partner", "className?"];
    static template = "mail.partner_im_status";
    static defaultProps = { className: "" };
}
