import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { Component, onWillStart, plugin, props, proxy, types as t } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { useService } from "@web/core/utils/hooks";
import { TimeOffPlugin } from "../views/time_off_plugin";
import { TimeOffCard } from "./time_off_card";

export class TimeOffDashboard extends Component {
    static components = { TimeOffCard, DateTimeInput };
    static template = "hr_holidays.TimeOffDashboard";

    props = props({
        employeeId: t.or([t.number(), t.literal(null)]),
    });

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.newAllocRequest = useNewAllocationRequest();
        this.state = proxy({
            date: luxon.DateTime.now(),
            today: luxon.DateTime.now(),
            holidays: [],
            allocationRequestDaysHours: "",
        });

        plugin(TimeOffPlugin).onUpdateDashboard(() => this.loadDashboardData());

        onWillStart(async () => this.loadDashboardData());
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
        );
        this.state.holidays = dashboardData["allocation_data"];
        this.state.allocationRequestDaysHours = dashboardData["allocation_request_days_hours"];
        this.hasAccrualAllocation = dashboardData["has_accrual_allocation"];
        this.hasFutureAllocation = dashboardData["has_future_allocation"];
    }

    resetDate() {
        this.state.date = luxon.DateTime.now();
        this.loadDashboardData();
    }

    openNewAllocation() {
        this.newAllocRequest({
            employeeId: this.props.employeeId,
        });
    }
}
