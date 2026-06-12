import { Component, props, t } from "@odoo/owl";

export class OdooLogo extends Component {
    static template = "point_of_sale.OdooLogo";
    props = props({
        class: t.string().optional(""),
        style: t.string().optional(""),
        monochrome: t.boolean().optional(false),
    });
}
