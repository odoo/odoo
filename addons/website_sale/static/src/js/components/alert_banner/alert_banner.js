import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class AlertBanner extends Component {
    static template = "website_sale.AlertBanner";
    static props = {
        level: { type: String, optional: true },
        message: String,
        className: { type: String, optional: true },
    }
    static defaultProps = {
        level: "warning",
        className: "",
    }
}

registry.category("public_components").add("website_sale.AlertBanner", AlertBanner);
