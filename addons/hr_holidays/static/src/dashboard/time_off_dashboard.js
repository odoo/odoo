import { useState } from "@web/owl2/utils";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TimeOffCard } from "./time_off_card";
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Component, onWillStart } from "@odoo/owl";
import { userHasEmployeeInCurrentCompany } from "@hr_holidays/utils";

function useUniqueDialog() {
    const displayDialog = useOwnedDialogs();
    let close = null;
    return (...args) => {
        if (close) {
            close();
        }
        close = displayDialog(...args);
    };
}

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
        this.displayDialog = useUniqueDialog();
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
    }

    async newAllocationRequest() {
        const hasEmployee = await userHasEmployeeInCurrentCompany(this.orm);
        if (!this.props.employeeId && !hasEmployee) {
            this.displayDialog(AlertDialog, {
                title: _t("UserError"),
                body: _t("This operation is not allowed as you are not linked to an employee in the current company."),
            });
            return;
        }
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
