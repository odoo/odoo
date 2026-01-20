import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendar extends models.ServerModel {
    _name = "resource.calendar";

    _records = [{ id: 1, name: "Variable", schedule_type: "variable" }];

    _views = {
        form: `
            <form class="o_resource_form">
                <sheet class="mw-100 pb-2 d-flex flex-grow-1">
                    <field name="schedule_type" widget="schedule_type_confirm_radio" options="{'horizontal': true}" class="o_field_radio"/>
                    <field nolabel="1" name="attendance_ids" widget="resource_calendar_attendance_calendar_one2many" class="flex-grow-1"/>
                </sheet>
            </form>
        `,
    };
}
