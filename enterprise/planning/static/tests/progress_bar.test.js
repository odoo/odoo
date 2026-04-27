import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { PlanningEmployeeAvatar } from "@planning/views/planning_gantt/planning_employee_avatar";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

defineMailModels();

test("ProgressBar: Default role of material resources should be in muted.", async () => {
    await mountWithCleanup(PlanningEmployeeAvatar, {
        props: {
            resId: 1,
            resModel: "It'sAMe",
            displayName: "SuperMarioOnThePs4 (WAHOO)",
        },
    });
    expect("span:last").toHaveClass("text-muted");
});
