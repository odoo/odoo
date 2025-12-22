import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class ProjectUpdate extends models.Model {
    _name = "project.update";

    status = fields.Selection({
        selection: [
            ["on_track", "On Track"],
            ["at_risk", "At Risk"],
            ["off_track", "Off Track"],
            ["on_hold", "On Hold"],
            ["done", "Done"],
        ],
    });

    _records = [{ id: 1, status: "on_track" }];
}

defineMailModels();
defineModels([ProjectUpdate]);

test("project.update (kanban): check that ProjectStatusWithColorSelectionField is displaying the correct informations", async () => {
    await mountView({
        resModel: "project.update",
        type: "kanban",
        arch: `
            <kanban  class="o_kanban_test">
                <template>
                    <t t-name="card">
                        <field name="status" widget="status_with_color" readonly="1" status_label="test status label"/>
                    </t>
                </template>
            </kanban>
        `,
    });

    expect("div[name='status'] .o_color_bubble_20").toHaveCount(1, {
        message: "In readonly a status bubble should be displayed",
    });
    expect("div[name='status'] .o_stat_text:contains('test status label')").toHaveCount(1, {
        message: "If the status_label prop has been set, its value should be displayed as well",
    });
    expect("div[name='status'] .o_stat_value:contains('On Track')").toHaveCount(1, {
        message: "The value of the selection should be displayed",
    });
});
