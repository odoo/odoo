import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

import { markup } from "@odoo/owl";

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    name = fields.Char();

    _views = {
        list: `<list js_class="attendance_list_view"><field name="name"/></list>`,
        kanban: `
            <kanban js_class="attendance_kanban_view">
                <templates><t t-name="card"><field name="name"/></t></templates>
            </kanban>`,
    };
}

defineModels([HrAttendance]);
defineMailModels();

onRpc("hr.attendance", "get_attendance_dashboard_data", () => ({}));

const noContentHelp = markup('<p class="o_view_nocontent_smiling_face">Help of the action</p>');

for (const type of ["list", "kanban"]) {
    for (const [isManager, context, onboarding] of [
        [true, {}, true],
        [true, { my_attendances: true }, false],
        [false, {}, false],
    ]) {
        test(`empty ${type}: onboarding ${onboarding} (HR user ${isManager}, ${JSON.stringify(context)})`, async () => {
            onRpc("has_group", () => isManager);
            await mountView({ type, resModel: "hr.attendance", context, noContentHelp });
            expect(".o_nocontent_help .btn:contains(Try the kiosk)").toHaveCount(onboarding ? 1 : 0);
            expect(".o_view_nocontent_smiling_face").toHaveCount(onboarding ? 0 : 1);
        });
    }
}
