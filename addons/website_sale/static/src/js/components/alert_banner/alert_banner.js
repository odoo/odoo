import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class AlertBanner extends Component {
    static template = "website_sale.AlertBanner";
    props = props({
        level: t.string().optional("warning"),
        message: t.string(),
        className: t.string().optional(""),
    });
}

registry.category("public_components").add("website_sale.AlertBanner", AlertBanner);
