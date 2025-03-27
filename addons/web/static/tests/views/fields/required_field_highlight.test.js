import { expect, test } from "@odoo/hoot";

import {
    clickSave,
    defineModels,
    fields,
    fieldInput,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    partner_name = fields.Char({ required: true });
}

defineModels([Partner]);

test("test required fields have invalid class when required field value cleared", async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="partner_name"/>
            </form>
        `,
    });

    expect(`div[name="partner_name"]`).not.toHaveClass("o_field_invalid");

    await fieldInput("partner_name").edit("test", { confirm: false });
    await clickSave();
    expect(`div[name="partner_name"]`).not.toHaveClass("o_field_invalid");

    await fieldInput("partner_name").clear();
    expect(`div[name="partner_name"]`).toHaveClass("o_field_invalid");
});
