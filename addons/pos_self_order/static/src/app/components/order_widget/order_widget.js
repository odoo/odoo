import { Component, props, t } from "@odoo/owl";

export class OrderWidget extends Component {
    static template = "pos_self_order.OrderWidget";
    props = props({
        removeTopClasses: t.boolean().optional(),
    });
}
