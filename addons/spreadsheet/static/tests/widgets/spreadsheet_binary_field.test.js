import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

const BINARY_FILE = "R0lGODlhDAMAKIFAF5LAP/zxANyuAP/gaP///wACH5BAEAUALAw";

class SpreadsheetDashboard extends models.Model {
    _name = "spreadsheet.dashboard";
    document = fields.Binary();
    _records = [{ document: BINARY_FILE }];
}

defineMailModels();
defineModels([SpreadsheetDashboard]);

onRpc("has_group", () => true);

test("Downloading dashboard json file should be disabled in list view", async () => {
    await mountView({
        resModel: "spreadsheet.dashboard",
        type: "list",
        arch: `<list><field name="document" widget="spreadsheetBinary" filename="dashboard.json"/></list>`,
    });
    click(`.fa-download`);
    await animationFrame();
    expect(`.modal-header`).toHaveText("Warning");
    expect(`.modal-body`).toHaveText(
        "Dashboard JSON file cannot be downloaded here. Please open the dashboard, activate debug mode and go the File → Download as JSON."
    );
});
