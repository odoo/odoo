import { Component, props, types as t } from "@odoo/owl";

export class DashboardBlock extends Component {
    static template = "mysubscription.DashboardBlock";

    props = props({
        subtitle: t.string().optional(),
    });

    setup() {};
}
