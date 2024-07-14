/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class ConnectedUntil extends Component {
    static template = "account_online_synchronization.ConnectedUntil";
    static props = { ...standardWidgetProps, };

    setup() {
        this.state = useState({
            isHovered: false,
        });
        this.style = "text-nowrap w-100";
        if (this.props.record.data.expiring_synchronization_due_day <= 7) {
            this.style +=
                this.props.record.data.expiring_synchronization_due_day <= 3
                    ? " text-danger"
                    : " text-warning";
        }
        this.action = useService("action");
        this.orm = useService("orm");
    }

    onMouseEnter() {
        this.state.isHovered = true;
    }

    onMouseLeave() {
        this.state.isHovered = false;
    }

    async extendConnection() {
        const action = await this.orm.call('account.journal', 'action_extend_consent', [this.props.record.resId], {});
        this.action.doAction(action);
    }
}

export const connectedUntil = {
    component: ConnectedUntil,
};

registry.category("view_widgets").add("connected_until_widget", connectedUntil);
