import { models } from "@web/../tests/web_test_helpers";

export class HrWorkEntry extends models.ServerModel {
    _name = "hr.work.entry";

    _views = {
        "form,multi_create_form": `
            <form>
                <field name="employee_id" invisible="1"/>
            </form>
        `,
        calendar: `
            <calendar
                date_start="date"
                date_stop="date" 
                mode="month"
                scales="month"
                month_overflow="0"
                quick_create="0"
                color="color"
                event_limit="9"
                show_date_picker="0"
                multi_create_view="multi_create_form"
                js_class="work_entries_calendar">
            </calendar>
        `,
    };

    action_split(workEntryIds, vals) {}
}
