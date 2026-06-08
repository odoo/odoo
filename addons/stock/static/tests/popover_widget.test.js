import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    json_data = fields.Char();

    _records = [
        {
            id: 1,
            json_data:
                '{"color": "text-danger", "msg": "var that = self // why not?", "title": "JS Master"}',
        },
    ];
}

defineModels([Partner]);
defineMailModels();

test("Test creation/usage form popover widget", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="json_data" widget="popover_widget"/>
            </form>`,
        resId: 1,
    });
    expect(".popover").toHaveCount(0);
    expect(".fa-info-circle.text-danger").toHaveCount(1);
    await contains(".fa-info-circle.text-danger").click();
    expect(".popover").toHaveCount(1);
    expect(".popover").toHaveText("JS Master\nvar that = self // why not?");
});
