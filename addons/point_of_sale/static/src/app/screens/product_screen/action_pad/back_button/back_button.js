import { Component, props, t } from "@odoo/owl";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";
    props = props({
        onClick: t.function(),
        class: t.object().optional(),
    });
}
