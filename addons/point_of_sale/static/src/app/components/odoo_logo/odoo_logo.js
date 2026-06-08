import { Component, props, types } from "@odoo/owl";

export class OdooLogo extends Component {
    static template = "point_of_sale.OdooLogo";
    props = props(
        {
            "class?": types.string(),
            "style?": types.string(),
            "monochrome?": types.boolean(),
        },
        {
            class: "",
            style: "",
            monochrome: false,
        }
    );
}
