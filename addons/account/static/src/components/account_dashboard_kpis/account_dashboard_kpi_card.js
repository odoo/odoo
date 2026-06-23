import { Component } from "@odoo/owl";

export class AccountDashboardKpiCard extends Component {
    static template = "account.AccountDashboardKpiCard";
    static props = {
        card: Object,
        onClick: Function,
    };

    onClick() {
        if (this.props.card.action_id) {
            this.props.onClick(this.props.card);
        }
    }
}
