/** @odoo-module */

import { Component } from "@odoo/owl";

export class OdooLogo extends Component {
    static template = "point_of_sale.OdooLogo";
    static props = {
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        monochrome: { type: Boolean, optional: true },
    };
    static defaultProps = {
        class: "",
        style: "",
        monochrome: false,
    };
}
