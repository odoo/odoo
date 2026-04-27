import {
    clickSave,
    contains,
    makeMockServer,
    mockService,
    mountView,
} from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

describe.current.tags("desktop");
defineHrModels();

test("editing the 'lang' field and saving it triggers a 'reload_context'", async function () {
    const { env } = await makeMockServer();
    const userId = env["fake.user"].create({
        name: "Aline",
        lang: "fr",
    });
    mockService("action", {
        doAction(action) {
            expect.step(action);
        },
    });
    await mountView({
        type: "form",
        resModel: "fake.user",
        arch: `
            <form js_class="hr_user_preferences_form">
                <field name="name"/>
                <field name="lang"/>
            </form>`,
        resId: userId,
    });
    await contains("[name='name'] input").edit("John");
    await clickSave();
    expect.verifySteps([]);
    await contains("[name='lang'] input").edit("En");
    await clickSave();
    expect.verifySteps(["reload_context"]);
});

test("employees should only have their versions in the versions_timeline", async function() {
    const { env } = await makeMockServer();
    const [version_1, version_2, version_3] = env["hr.version"].create([
        { name: "Version 1", date_version: "2026-01-01" },
        { name: "Version 2", date_version: "2026-01-10" },
        { name: "Version 3", date_version: "2026-01-20" },
    ])
    const [first_employee, second_employee] = env["hr.employee"].create([
        { version_ids: [version_1] },
        { version_ids: [version_2, version_3] },
    ])
    await mountView({
        type: "form",
        resModel: "hr.employee",
        arch: `
            <form>
                <field name="version_id" widget="versions_timeline"/>
            </form>`,
        domain: [],
        resId: first_employee,
        resIds: [first_employee, second_employee],
    });
    // Employee A
    expect(".o_statusbar_status button:contains('Version 1')").toHaveCount(1);
    expect(".o_statusbar_status button:contains('Version 2')").toHaveCount(0);
    expect(".o_statusbar_status button:contains('Version 3')").toHaveCount(0);
    await contains(".o_pager button.o_pager_next:enabled").click();
    // Employee B
    expect(".o_statusbar_status button:contains('Version 1')").toHaveCount(0);
    expect(".o_statusbar_status button:contains('Version 2')").toHaveCount(1);
    expect(".o_statusbar_status button:contains('Version 3')").toHaveCount(1);
    await contains(".o_pager button.o_pager_previous:enabled").click();
    // Employee A
    expect(".o_statusbar_status button:contains('Version 1')").toHaveCount(1);
    expect(".o_statusbar_status button:contains('Version 2')").toHaveCount(0);
    expect(".o_statusbar_status button:contains('Version 3')").toHaveCount(0);
})
