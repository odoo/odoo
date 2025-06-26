import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";

import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    model = fields.Char({
        string: "Resource Model",
    });
    res_id = fields.Many2oneReference({
        string: "Resource Id",
        model_field: "model",
        relation: "partner.type",
    });

    _records = [
        { id: 1, model: "partner.type", res_id: 10 },
        { id: 2, res_id: false },
    ];
}

class PartnerType extends models.Model {
    name = fields.Char();

    _records = [
        { id: 10, name: "gold" },
        { id: 14, name: "silver" },
    ];
}

defineModels([Partner, PartnerType]);

onRpc("has_group", () => true);

test("Many2OneReferenceIntegerField in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="res_id" widget="many2one_reference_integer"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("10");
});

test("Many2OneReferenceIntegerField in list view", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        resId: 1,
        arch: '<list><field name="res_id" widget="many2one_reference_integer"/></list>',
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["10", ""]);
});

test("Many2OneReferenceIntegerField: unset value in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: '<form><field name="res_id" widget="many2one_reference_integer"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("");
});
