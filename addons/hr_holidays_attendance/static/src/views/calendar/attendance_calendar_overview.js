import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AttendanceCalendarOverview } from "@hr_attendance/components/attendance_calendar/attendance_calendar_overview";
import { TimeOffFormViewDialog } from "@hr_holidays/views/view_dialog/form_view_dialog";

patch(AttendanceCalendarOverview.prototype, {
    setup() {
        super.setup();
        this.displayDialog = useOwnedDialogs();
        this.state = useState({
            ...this.state,
            remainingExtraHours: 0,
        });
    },

    async loadData() {
        const { start, end } = this.props.dateRange;
        const employeeId = this.env.searchModel.context.active_id;
        const attendace_data = await this.orm.call(
            "hr.employee",
            "get_attendace_data_by_employee",
            [employeeId, start, end]
        );
        this.state.workedHours = attendace_data[employeeId].worked_hours;
        this.state.extraHours = attendace_data[employeeId].overtime_hours;
        this.state.remainingExtraHours = attendace_data[employeeId].unspent_compensable_overtime;
    },

    newTimeOffRequest() {
        const context = {};
        if (this.env.searchModel.context.active_id && this.env.searchModel.context.active_model === "hr.employee") {
            context["default_employee_id"] = this.env.searchModel.context.active_id;
        }
        context['form_view_ref'] = "hr_holidays.hr_leave_view_form_dashboard_new_time_off";
        this.displayDialog(TimeOffFormViewDialog, {
            resModel: "hr.leave",
            title: _t("New Time Off"),
            size: "md",
            onRecordSaved: () => { this.loadData(); },
            onRecordDeleted: (record) => {},
            onLeaveCancelled: (record) => {},
            context: context,
        });
    }
})
