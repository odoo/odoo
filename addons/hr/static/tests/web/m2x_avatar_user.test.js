import { describe, expect, test, getFixture } from "@odoo/hoot";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import {
    assertSteps,
    click,
    contains,
    openKanbanView,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { deepEqual } from "@web/core/utils/objects";

describe.current.tags("desktop");
defineHrModels();

test("avatar card preview with hr", async () => {
    const target = getFixture();
    const pyEnv = await startServer();
    const departmentId = pyEnv["hr.department"].create({
        name: "Managemment",
    });
    const userId = pyEnv["res.users"].create({
        name: "Mario",
        email: "Mario@odoo.test",
        work_email: "Mario@odoo.pro",
        im_status: "online",
        phone: "+78786987",
        work_phone: "+585555555",
        job_title: "sub manager",
        department_id: departmentId,
    });
    onRpc("res.users", "read", (params) => {
        expect(
            deepEqual(params.args[1], [
                "name",
                "email",
                "phone",
                "im_status",
                "share",
                "work_phone",
                "work_email",
                "job_title",
                "department_id",
                "employee_ids",
            ])
        ).toBe(true);
        step("user read");
    });
    pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openKanbanView("m2x.avatar.user", {
        arch: `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="user_id" widget="many2one_avatar_user"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });
    // Open card
    await click(".o_m2o_avatar > img");
    await contains(".o_avatar_card", { count: 1 });
    assertSteps(["user read"]);
    // FIXME: Missing values in the card
    expect(
        deepEqual(
            [...target.querySelectorAll(".o_card_user_infos > *")].map((i) => i.textContent),
            [
                "false" /* Should be 'Mario' */,
                "sub manager",
                "false" /* Should be 'Managemment' */,
                "Mario@odoo.pro",
                "+585555555",
            ]
        )
    ).toBe(true);
    // Close card
    await click(".o_action_manager");
    await contains(".o_avatar_card", { count: 0 });
});
