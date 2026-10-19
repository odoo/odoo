import { Component, useProps, t } from "@odoo/owl";

export class OrderWidget extends Component {
    static template = "pos_self_order.OrderWidget";
    props = useProps({
        removeTopClasses: t.boolean().optional(),
    });
}
