/** @odoo-module native */
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { DateTimeInput } from "@web/components/datetime";
import { luxon } from "@web/core/l10n/luxon";
import { useBus, useService } from "@web/core/utils/hooks";

import { TimeOffCard } from "./time_off_card.js";

export class TimeOffDashboard extends Component {
    static components = { TimeOffCard, DateTimeInput };
    static template = "hr_holidays.TimeOffDashboard";
    static props = ["employeeId"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.newRequest = useNewAllocationRequest();
        this.state = useState({
            date: luxon.DateTime.now(),
            today: luxon.DateTime.now(),
            holidays: [],
            allocationRequests: 0,
        });
        useBus(this.env.timeOffBus, "update_dashboard", async () => {
            await this.loadDashboardData();
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    getContext() {
        const context = {};
        if (this.props && this.props.employeeId !== null) {
            context["employee_id"] = this.props.employeeId;
        }
        return context;
    }

    async loadDashboardData(date = false) {
        const context = this.getContext();
        if (date) {
            this.state.date = date;
        }
        const dashboardData = await this.orm.call(
            "hr.employee",
            "get_time_off_dashboard_data",
            [this.state.date],
            { context },
        );
        this.state.holidays = dashboardData["allocation_data"];
        this.state.allocationRequests = dashboardData["allocation_request_amount"];
        this.hasAccrualAllocation = dashboardData["has_accrual_allocation"];
    }

    async newAllocationRequest() {
        await this.newRequest(this.props.employeeId);
    }

    resetDate() {
        this.state.date = luxon.DateTime.now();
        this.loadDashboardData();
    }

    async openPendingRequests() {
        if (!this.state.allocationRequests) {
            return;
        }
        const action = await this.orm.call(
            "hr.leave.allocation",
            "open_pending_requests",
            [],
            {
                context: this.getContext(),
            },
        );
        this.actionService.doAction(action);
    }
}
