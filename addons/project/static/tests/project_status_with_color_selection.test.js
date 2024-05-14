import { describe, expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("Check that ProjectStateSelectionField does not propose `Set Status`", async () => {
    await mountView({
        resModel: "project.update",
        type: "kanban",
        arch: `
            <kanban class="o_kanban_test">
                <field name="status"/>
                <field name="id"/>
                <template>
                    <t t-name="kanban-box">
                        <div>
                            <field name="status" widget="status_with_color" readonly="1" status_label="test status label"/>
                        </div>
                    </t>
                 </template>
            </kanban>`,
    });
    expect("div[name='status'] .o_color_bubble_20").toBeDisplayed();
    expect("div[name='status'] .o_stat_text").toHaveText("test status label");
    expect("div[name='status'] .o_stat_value").toHaveText("On Track");
});
