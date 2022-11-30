/** @odoo-module **/

import { Component } from "@odoo/owl";

export class PartnerImStatus extends Component {}

Object.assign(PartnerImStatus, {
    props: ["partner", "className?"],
    template: "mail.partner_im_status",
    defaultProps: { className: "" },
});
