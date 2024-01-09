/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { clickSave, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class ResPartner extends models.Model {
    _name = "res.partner";

    int_field = fields.Integer();
}

defineModels([ResPartner]);

test("no autofocus with disable_autofocus option", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: /* xml */ `
            <form disable_autofocus="1">
                <field name="int_field" />
            </form>
        `,
    });

    expect(`.o_field_widget[name="int_field"] input`).not.toBeFocused();

    await clickSave();

    expect(`.o_field_widget[name="int_field"] input`).not.toBeFocused();
});
