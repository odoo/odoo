import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { fields, mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectProject } from "./project_models";

defineProjectModels();

test("project.project (kanban): check that ProjectStateSelectionField does not propose `Set Status`", async () => {
    Object.assign(ProjectProject._fields, {
        last_update_status: fields.Selection({
            string: "Status",
            selection: [
                ["on_track", "On Track"],
                ["at_risk", "At Risk"],
                ["off_track", "Off Track"],
                ["on_hold", "On Hold"],
            ],
        }),
        last_update_color: fields.Integer({ string: "Update State Color" }),
    });
    ProjectProject._records = [
        {
            id: 1,
            last_update_status: "on_track",
            last_update_color: 20,
        },
    ];

    await mountView({
        resModel: "project.project",
        type: "kanban",
        arch: `
            <kanban class="o_kanban_test">
                <template>
                    <t t-name="card">
                        <field name="last_update_status" widget="project_state_selection"/>
                    </t>
                </template>
            </kanban>
        `,
    });
    await click("div[name='last_update_status'] button.dropdown-toggle");
    expect(".dropdown-menu .dropdown-item:contains('Set Status')").toHaveCount(0);
});
