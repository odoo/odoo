import { TimeOffCard } from "./time_off_card";
import { TimeOffNewDropdown } from "../components/time_off_new_dropdown/time_off_new_dropdown";
import { useBus, useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Component, useState, onWillStart } from "@odoo/owl";

export class TimeOffDashboard extends Component {
    static components = { TimeOffCard, TimeOffNewDropdown, DateTimeInput };
    static template = "hr_holidays.TimeOffDashboard";
    static props = ["employeeId"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
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
            this.loadDashboardData();
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
        const dashboardData = await this.orm.call(
            "hr.employee",
            "get_time_off_dashboard_data",
            [this.state.date],
            { context }
        )
        this.state.holidays = dashboardData['allocation_data'];
        this.state.allocationRequests = dashboardData['allocation_request_amount'];
        this.hasAccrualAllocation = dashboardData['has_accrual_allocation'];
        this.hasFutureAllocation = dashboardData['has_future_allocation'];
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
