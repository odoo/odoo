/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import { waitForChannels, waitNotifications } from "@bus/../tests/bus_test_helpers";

import {
    MockServer,
    defineModels,
    mountView,
    models,
    makeMockEnv,
} from "@web/../tests/web_test_helpers";

import { hrModels } from "@hr/../tests/hr_test_helpers";
import { serverState } from "@web/../tests/_framework/mock_server_state.hoot";


class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
    _records = [
        {
            id: 22,
            name: "Test Employee",
            hr_icon_display: "presence_absent",
            hr_presence_state: "absent",
            user_id: serverState.userId,
        },
    ];
}

defineModels({ ...hrModels, HrEmployee });

test("Check presence status state", async function () {
    const env = await makeMockEnv();
    const channel = "hr.employee_22";

    env.services.bus_service.addChannel(channel);
    await waitForChannels([channel]);

    await mountView({
        type: "kanban",
        resModel: "hr.employee",
        arch: `
            <kanban class="o_hr_employee_kanban" sample="1" duplicate="false">
                <templates>
                    <t t-name="card" class="flex-row">
                        <field name="name"/>
                        <field name="hr_icon_display" widget="hr_presence_status"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    expect(".o_employee_availability span").toHaveAttribute("title", "Absent");

    await MockServer.env["bus.bus"]._sendone(channel, "hr.employee/presence", {
        hr_icon_display: "presence_present",
        hr_presence_state: "present",
        employee_id: 22,
    });

    await waitNotifications([env, "hr.employee/presence"]);
    await runAllTimers();

    expect(".o_employee_availability span").toHaveAttribute("title", "Present");
});
