import { Component, t, useProps } from "@odoo/owl";

export class AccountDashboardKpiCard extends Component {
    static template = "account.AccountDashboardKpiCard";

    props = useProps({
        card: t.object(),
        onClick: t.function(),
    });

    onClick() {
        if (this.props.card.action_id) {
            this.props.onClick(this.props.card);
        }
    }
}
