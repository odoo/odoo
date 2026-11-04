import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

class TestSpreadsheet extends models.Model {
    _name = "test.spreadsheet";
    spreadsheet_binary_data = fields.Binary();
    _records = [{ spreadsheet_binary_data: "R0lGODlhDAMAKIFAF5LAP/zxANyuAP/gaP//wACH5BAEAUALAw" }];
}

defineMailModels();
defineModels([TestSpreadsheet]);

onRpc("has_group", () => true);

test("Downloading dashboard json file should be disabled in list view", async () => {
    onRpc("/web/content", () => {
        expect.step("We shouldn't be getting the file.");
    });
    await mountView({
        resModel: "test.spreadsheet",
        type: "list",
        arch: `<list>
                    <field
                        name="spreadsheet_binary_data"
                        widget="binary_spreadsheet"
                        filename="dashboard.json"
                    />
                </list>`,
    });
    click(`.o_field_widget[name="spreadsheet_binary_data"]`);
    await animationFrame();
    expect.verifySteps([]);
});

test("Download button for dashboard json file should be hidden in list view", async () => {
    await mountView({
        resModel: "test.spreadsheet",
        type: "list",
        arch: `<list>
                    <field
                        name="spreadsheet_binary_data"
                        widget="binary_spreadsheet"
                        filename="dashboard.json"
                    />
                </list>`,
    });
    expect(`.o_field_widget[name="spreadsheet_binary_data"] .fa-download`).toHaveCount(0, {
        message: "The download button should be hidden",
    });
});
