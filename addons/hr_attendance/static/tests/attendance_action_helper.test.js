import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

// The server inlines the help view of the attendances (hr_attendance_view_help) in the list and kanban archs: the
// onboarding out of My Attendances, a welcome of the employee (data of get_help_data) on My Attendances.
const help = `
    <help data_method="get_help_data">
        <t invisible="not context.get('my_attendances')">
            <p class="o_view_nocontent_smiling_face"><t t-out="data.welcome"/></p>
        </t>
        <div invisible="context.get('my_attendances')">
            <a class="btn btn-primary">Try the kiosk</a>
        </div>
    </help>`;

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    name = fields.Char();

    get_help_data() {
        return { welcome: "Welcome Light! Log your attendances here." };
    }

    _views = {
        list: `<list js_class="attendance_list_view"><field name="name"/>${help}</list>`,
        kanban: `
            <kanban js_class="attendance_kanban_view">
                <templates><t t-name="card"><field name="name"/></t></templates>
                ${help}
            </kanban>`,
    };
}

defineModels([HrAttendance]);
defineMailModels();

onRpc("hr.attendance", "get_attendance_dashboard_data", () => ({}));

for (const type of ["list", "kanban"]) {
    for (const [context, onboarding] of [
        [{}, true],
        [{ my_attendances: true }, false],
    ]) {
        test(`empty ${type}: onboarding ${onboarding} (${JSON.stringify(context)})`, async () => {
            await mountView({ type, resModel: "hr.attendance", context });
            expect(".o_view_nocontent .btn:contains(Try the kiosk)").toHaveCount(onboarding ? 1 : 0);
            expect(".o_view_nocontent_smiling_face").toHaveCount(onboarding ? 0 : 1);
            if (!onboarding) {
                expect(".o_view_nocontent_smiling_face").toHaveText("Welcome Light! Log your attendances here.");
            }
        });
    }
}
