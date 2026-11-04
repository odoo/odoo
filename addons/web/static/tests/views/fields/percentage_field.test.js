import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";
import { clear, click, edit } from "@odoo/hoot-dom";

class Partner extends models.Model {
    float_field = fields.Float({
        string: "Float_field",
        digits: [0, 1],
    });
    _records = [{ float_field: 0.44444 }];
}

defineModels([Partner]);

test("PercentageField in form view", async () => {
    expect.assertions(5);

    onRpc("web_save", ({ args }) => {
        expect(args[1].float_field).toBe(0.24);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="float_field" widget="percentage"/></form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=float_field] input").toHaveValue("44.4");
    expect(".o_field_widget[name=float_field] span").toHaveText("%", {
        message: "The input should be followed by a span containing the percentage symbol.",
    });

    await click("[name='float_field'] input");
    await edit("24");
    expect("[name='float_field'] input").toHaveValue("24");

    await clickSave();

    expect(".o_field_widget input").toHaveValue("24");
});

test("percentage field with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="float_field" widget="percentage" placeholder="Placeholder"/></form>`,
    });

    await click(".o_field_widget[name='float_field'] input");
    await clear();

    expect(".o_field_widget[name='float_field'] input").toHaveProperty(
        "placeholder",
        "Placeholder"
    );
    expect(".o_field_widget[name='float_field'] input").toHaveAttribute(
        "placeholder",
        "Placeholder"
    );
});

test("PercentageField in form view without rounding error", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="float_field" widget="percentage"/></form>`,
    });

    await click("[name='float_field'] input");
    await edit("28");

    expect("[name='float_field'] input").toHaveValue("28");
});
