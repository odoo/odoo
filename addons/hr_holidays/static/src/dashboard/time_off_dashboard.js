/* @odoo-module */

import { TimeOffCard } from "./time_off_card";
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { useBus, useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class TimeOffDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.newRequest = useNewAllocationRequest();
        this.state = useState({
            holidays: [],
        });
        useBus(this.env.timeOffBus, "update_dashboard", async () => {
            await this.loadDashboardData();
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const context = {};
        if (this.props.employeeId !== null) {
            context["employee_id"] = this.props.employeeId;
        }

        this.state.holidays = await this.orm.call("hr.leave.type", "get_days_all_request", [], {
            context: context,
        });
    }
    async newAllocationRequest() {
        await this.newRequest(this.props.employeeId);
    }
}

TimeOffDashboard.components = { TimeOffCard };
TimeOffDashboard.template = "hr_holidays.TimeOffDashboard";
TimeOffDashboard.props = ["employeeId"];
