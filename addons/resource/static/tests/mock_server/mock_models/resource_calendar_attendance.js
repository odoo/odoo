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
                <field name="duration_based" invisible="1"/>
                <group>
                    <field string="Duration" name="duration_hours" widget="float_time"/>
                    <label string="Time" for="hour_from"/>
                    <span class="d-flex align-items-baseline gap-2">
                        <field name="hour_from" nolabel="1" class="o_hr_narrow_field" widget="float_time"/>
                        <i class="fa fa-long-arrow-right" title="to"/>
                        <field name="hour_to" nolabel="1" class="o_hr_narrow_field" widget="float_time"/>
                    </span>
                    <field name="recurrency" widget="boolean_toggle" options="{'autosave': False}"/>
                    <label for="recurrency_interval" string="Repeat every" invisible="not recurrency"/>
                    <span class="d-flex gap-2" invisible="not recurrency">
                        <field name="recurrency_interval" style="width: 2rem" required="recurrency"/>
                        <field name="recurrency_type" style="width: 5rem" required="recurrency"/>
                        <field name="recurrency_end_type" class="oe_inline w-auto" required="recurrency"/>
                        <field name="recurrency_count" invisible="recurrency_end_type != 'times'" style="width: 2rem" required="recurrency_end_type == 'times'"/>
                        <field name="recurrency_until" invisible="recurrency_end_type != 'date'" required="recurrency_end_type == 'date'"/>
                    </span>
                </group>
            </form>
        `,
    };
}
