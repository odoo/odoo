/* @odoo-module */

import { TimeOffCard } from "./time_off_card";
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { useBus, useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Component, useState, onWillStart } from "@odoo/owl";

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
            const context = this.getContext();
            this.hasAccrualAllocation = await this.orm.call(
                "hr.leave.type",
                "has_accrual_allocation",
                [],
                {
                    context: context,
                }
            );
        });
    }

    getContext() {
        const context = { from_dashboard: true };
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
        this.state.holidays = await this.orm.call(
            "hr.leave.type",
            "get_allocation_data_request",
            [this.state.date, false],
            {
                context: context,
            }
        );
        this.state.allocationRequests = await this.orm.call(
            "hr.employee",
            "get_allocation_requests_amount",
            [],
            {
                context: context,
            }
        );
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
        const action = await this.orm.call("hr.leave", "open_pending_requests", [], {
            context: this.getContext(),
        });
        this.actionService.doAction(action);
    }
}
