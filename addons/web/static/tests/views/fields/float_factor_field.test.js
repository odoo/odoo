import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    contains,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    qux = fields.Float();

    _records = [{ id: 1, qux: 9.1 }];
}

defineModels([Partner]);

test("FloatFactorField in form view", async () => {
    expect.assertions(3);

    onRpc("partner", "web_save", ({ args }) => {
        // 2.3 / 0.5 = 4.6
        expect(args[1].qux).toBe(4.6, { message: "the correct float value should be saved" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="qux" widget="float_factor" options="{'factor': 0.5}" digits="[16,2]" />
                </sheet>
            </form>`,
    });
    expect(".o_field_widget[name='qux'] input").toHaveValue("4.55", {
        message: "The value should be rendered correctly in the input.",
    });

    await contains(".o_field_widget[name='qux'] input").edit("2.3");
    await clickSave();

    expect(".o_field_widget input").toHaveValue("2.30", {
        message: "The new value should be saved and displayed properly.",
    });
});

test("FloatFactorField comma as decimal point", async () => {
    expect.assertions(2);

    // patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "" });
    defineParams({
        lang_parameters: {
            decimal_point: ",",
            thousands_sep: "",
        },
    });
    onRpc("partner", "web_save", ({ args }) => {
        // 2.3 / 0.5 = 4.6
        expect(args[1].qux).toBe(4.6);
        expect.step("save");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="qux" widget="float_factor" options="{'factor': 0.5}" digits="[16,2]" />
                </sheet>
            </form>`,
    });

    await contains(".o_field_widget[name='qux'] input").edit("2,3");
    await clickSave();

    expect.verifySteps(["save"]);
});
