/* @odoo-module */

import { TimeOffCard } from "./time_off_card";
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { useBus, useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Component, useState, onWillStart } from "@odoo/owl";

export class TimeOffDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.newRequest = useNewAllocationRequest();
        this.state = useState({
            date: luxon.DateTime.now(),
            today: luxon.DateTime.now(),
            holidays: [],
        });
        useBus(this.env.timeOffBus, "update_dashboard", async () => {
            await this.loadDashboardData();
        });

        onWillStart(async () => {
            await this.loadDashboardData();
            const context = {};
            if (this.props && this.props.employeeId !== null) {
                context["employee_id"] = this.props.employeeId;
            }
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

    async loadDashboardData(date = false) {
        const context = { from_dashboard: true };
        if (this.props && this.props.employeeId !== null) {
            context["employee_id"] = this.props.employeeId;
        }
        if (date) {
            this.state.date = date;
        }
        this.state.holidays = await this.orm.call(
            "hr.leave.type",
            "get_allocation_data_request",
            [this.state.date],
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
}

TimeOffDashboard.components = { TimeOffCard, DateTimeInput };
TimeOffDashboard.template = "hr_holidays.TimeOffDashboard";
TimeOffDashboard.props = ["employeeId"];
