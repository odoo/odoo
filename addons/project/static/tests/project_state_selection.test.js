import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("Check that ProjectStateSelectionField does not propose `Set Status`", async () => {
    await mountView({
        resModel: "project.project",
        type: "kanban",
        arch: `
            <kanban class="o_kanban_test">
                <field name="last_update_status"/>
                <field name="last_update_color"/>
                <template>
                    <t t-name="kanban-box">
                        <div>
                            <field name="last_update_status" widget="project_state_selection"/>
                        </div>
                    </t>
                </template>
            </kanban>`,
    });
    await contains("div[name='last_update_status'] button.dropdown-toggle").click();
    expect(".dropdown-menu .dropdown-item:contains('Set Status')").not.toBeDisplayed();
});
