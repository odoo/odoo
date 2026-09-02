import { Component, useProps, t } from "@odoo/owl";

export class DashboardBlock extends Component {
    static template = "mysubscription.DashboardBlock";

    props = useProps({
        subtitle: t.string().optional(),
    });
}
