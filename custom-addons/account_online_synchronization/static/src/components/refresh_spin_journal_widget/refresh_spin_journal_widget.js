/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

class RefreshSpin extends Component {
    static template = "account_online_synchronization.RefreshSpin";
    static props = { ...standardWidgetProps };

    setup() {
        this.state = useState({
            isHovered: false,
            fetchingStatus: false,
            connectionStateDetails: null,
        });

        this.actionService = useService("action");
        this.busService = this.env.services.bus_service;
        this.user = useService("user");
        this.orm = useService("orm");
        this.state.fetchingStatus = this.props.record.data.online_sync_fetching_status;

        this.busService.subscribe("online_sync", (notification) => {
            if (notification?.id === this.recordId && notification?.connection_state_details) {
                this.state.connectionStateDetails = notification.connection_state_details;
            }
        });

        onWillStart(() => {
            this._initConnectionStateDetails();
        });
    }

    refresh() {
        this.actionService.restore(this.actionService.currentController.jsId);
    }

    onMouseEnter() {
        this.state.isHovered = true;
    }

    onMouseLeave() {
        this.state.isHovered = false;
    }

    async openAction() {
        /**
         * This function is used to open the action that the asynchronous process saved
         * on the databsase. It allows users to call the action when they want and not when
         * the process is over.
         */
        const action = await this.orm.call(
            "account.journal",
            "action_open_dashboard_asynchronous_action",
            [this.recordId],
        );
        this.actionService.doAction(action);
        this.state.connectionStateDetails = null;
    }

    async fetchTransactions() {
        /**
         * This function call the function to fetch transactions.
         * In the main case, we don't do anything after calling the function.
         * The idea is that websockets will update the status by themselves.
         * In one specific case, we have to return an action to the user to open
         * the Odoo Fin iframe to refresh the connection.
         */
        const action = await this.orm.call("account.journal", "manual_sync", [this.recordId]);
        this.state.connectionStateDetails = { status: "fetching" };
        if (action) {
            this.actionService.doAction(action);
        }
    }

    _initConnectionStateDetails() {
        /**
         * This function is used to get the last state of the connection (if there is one)
         */
        const kanbanDashboardData = JSON.parse(this.props.record.data.kanban_dashboard);
        this.state.connectionStateDetails = kanbanDashboardData?.connection_state_details;
    }

    get recordId() {
        return this.props.record.data.id;
    }

    get connectionStatus() {
        return this.state.connectionStateDetails?.status;
    }
}

export const refreshSpin = {
    component: RefreshSpin,
};

registry.category("view_widgets").add("refresh_spin_widget", refreshSpin);
