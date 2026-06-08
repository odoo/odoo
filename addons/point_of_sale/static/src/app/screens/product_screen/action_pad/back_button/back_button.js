import { Component, props, types } from "@odoo/owl";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";
    props = props({
        onClick: types.function(),
        "class?": types.object(),
    });
}
