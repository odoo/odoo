import { expect, test } from "@odoo/hoot";
import { queryText } from "@odoo/hoot-dom";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    float_field = fields.Float({ string: "Float field" });

    _records = [{ id: 1, float_field: 0.44444 }];
}

class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}

defineModels([Partner, User]);

test("basic flow in form view", async () => {
    onRpc("partner", "web_save", ({ args }) => {
        // 1.000 / 0.125 = 8
        expect.step(args[1].float_field.toString());
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="float_field" widget="float_toggle" options="{'factor': 0.125, 'range': [0, 1, 0.75, 0.5, 0.25]}" digits="[5,3]"/>
            </form>`,
    });

    expect(".o_field_widget").toHaveText("0.056", {
        message: "The formatted time value should be displayed properly.",
    });
    expect("button.o_field_float_toggle").toHaveText("0.056", {
        message: "The value should be rendered correctly on the button.",
    });

    await contains("button.o_field_float_toggle").click();

    expect("button.o_field_float_toggle").toHaveText("0.000", {
        message: "The value should be rendered correctly on the button.",
    });

    // note, 0 will not be written, it's kept in the _changes of the datapoint.
    // because save has not been clicked.

    await contains("button.o_field_float_toggle").click();

    expect("button.o_field_float_toggle").toHaveText("1.000", {
        message: "The value should be rendered correctly on the button.",
    });

    await clickSave();

    expect(".o_field_widget").toHaveText("1.000", {
        message: "The new value should be saved and displayed properly.",
    });

    expect.verifySteps(["8"]);
});

test("kanban view (readonly) with option force_button", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="float_field" widget="float_toggle" options="{'force_button': true}"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("button.o_field_float_toggle").toHaveCount(1, {
        message: "should have rendered toggle button",
    });

    const value = queryText("button.o_field_float_toggle");
    await contains("button.o_field_float_toggle").click();
    expect("button.o_field_float_toggle").not.toHaveText(value, {
        message: "float_field field value should be changed",
    });
});
