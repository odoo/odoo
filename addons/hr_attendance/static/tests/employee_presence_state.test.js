import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";

import { waitForChannels, waitNotifications } from "@bus/../tests/bus_test_helpers";
import { ResPartner as MailResPartner } from "@mail/../tests/mock_server/mock_models/res_partner";
import { MockServer, defineModels, mountView, models, makeMockEnv } from "@web/../tests/web_test_helpers";

import { hrModels } from "@hr/../tests/hr_test_helpers";

class ResPartner extends MailResPartner {
    _name = "res.partner";
    _records = [
        ...MailResPartner.prototype.constructor._records,
        {
            id: 12,
            name: "Test Partner",
        },
    ];
}

class HrEmployee extends models.ServerModel {
    _name = 'hr.employee'
    _records = [
        {
            id: 22,
            name: 'Test Employee',
            hr_icon_display: "presence_absent",
            hr_presence_state: "absent",
            work_contact_id: 12,
        }
    ]
}

defineModels({...hrModels, ResPartner, HrEmployee});

test("Check presence status state", async function () {
    const env = await makeMockEnv();
    env.services.bus_service.addChannel("hr_attendance_presence#12");
    await waitForChannels(["hr_attendance_presence#12"]);
    await mountView({
        type: "kanban",
        resModel: "hr.employee",
        arch: `
            <kanban class="o_hr_employee_kanban" sample="1" duplicate="false">
                <templates>
                    <t t-name="card" class="flex-row">
                        <field name="work_contact_id" invisible="1"/>
                        <field name="name"/>
                        <field name="hr_icon_display" widget="hr_presence_status"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    await expect(".o_employee_availability span").toHaveAttribute('title', 'Absent');
    await MockServer.env["bus.bus"]._sendone("hr_attendance_presence#12", "presence_status", {
        "channel": "hr_attendance_presence#12",
        "data": {
            "emp_id": 22,
            "status": 'presence_present',
        },
    });
    await waitNotifications([env, 'presence_status'])
    await runAllTimers();
    await expect(".o_employee_availability span").toHaveAttribute('title', 'Present');
});
