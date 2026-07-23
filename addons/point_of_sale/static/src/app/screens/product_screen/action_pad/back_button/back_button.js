import { Component, t, useProps } from "@odoo/owl";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";
    props = useProps({
        onClick: t.function(),
        class: t.object().optional(),
    });
}
