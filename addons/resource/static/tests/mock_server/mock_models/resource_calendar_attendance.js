import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendarAttendance extends models.ServerModel {
    _name = "resource.calendar.attendance";

    _views = {
        calendar: `
            <calendar string="Working Time"
                js_class="resource_calendar_attendance_calendar"
                date_start="date"
                date_stop="date"
                all_day="duration_based"
                mode="week"
                scales="week,month"
                month_overflow="0"
                multi_create_view="resource.view_resource_calendar_multi_create_form"
                show_date_picker="0">
                <field name="display_name"/>
                <field name="hour_from"/>
                <field name="hour_to"/>
                <field name="duration_hours"/>
            </calendar>
        `,
        form: `
            <form>
                <group>
                    <field string="Duration" name="duration_hours" widget="float_time"/>
                    <label string="Time" for="hour_from"/>
                    <span class="d-flex align-items-baseline gap-2">
                        <field name="hour_from" nolabel="1" class="o_hr_narrow_field" widget="float_time"/>
                        <i class="fa fa-long-arrow-right" title="to"/>
                        <field name="hour_to" nolabel="1" class="o_hr_narrow_field" widget="float_time"/>
                    </span>
                </group>
            </form>
        `,
    };
}
