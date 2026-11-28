import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["done", "Done"],
        ],
    });

    _records = [
        { id: 1, name: "first record", parent_id: 2, state: "draft" },
        { id: 2, name: "second record" },
    ];
}

defineModels([Partner]);

const arch = `
    <form js_class="next_form">
        <field name="name"/>
        <field name="parent_id"/>
    </form>`;

test("next_form displays a record", async () => {
    await mountView({ resModel: "partner", type: "form", arch, resId: 1 });
    expect(".o_field_widget[name=name] input").toHaveValue("first record");
    expect(".o_field_widget[name=parent_id]").toHaveText("second record");
    expect(".o_form_button_save").toHaveCount(0);
    expect(".o_form_button_cancel").toHaveCount(0);
});

test("next_form displays fields without component as text", async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form js_class="next_form">
                <field name="name" widget="unknown_widget"/>
                <field name="parent_id"/>
                <field name="state"/>
            </form>`,
        resId: 1,
    });
    // an unknown widget: the component of the type
    expect(".o_field_widget[name=name] input").toHaveValue("first record");
    // types without component: their value as text
    expect(".o_field_widget[name=parent_id] input").toHaveCount(0);
    expect(".o_field_widget[name=parent_id]").toHaveText("second record");
    expect(".o_field_widget[name=state]").toHaveText("Draft");
});

test("next_form saves the changes", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args);
    });
    await mountView({ resModel: "partner", type: "form", arch, resId: 1 });
    await contains(".o_field_widget[name=name] input").edit("changed");
    expect(".o_form_button_save").toHaveCount(1);

    await contains(".o_form_button_save").click();
    await animationFrame();
    expect.verifySteps([[[1], { name: "changed" }]]);
    expect(".o_field_widget[name=name] input").toHaveValue("changed");
    expect(".o_form_button_save").toHaveCount(0);
});

test("next_form discards the changes", async () => {
    onRpc("web_save", () => {
        expect.step("web_save");
    });
    await mountView({ resModel: "partner", type: "form", arch, resId: 1 });
    await contains(".o_field_widget[name=name] input").edit("changed");
    expect(".o_form_button_cancel").toHaveCount(1);

    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=name] input").toHaveValue("first record");
    expect(".o_form_button_save").toHaveCount(0);
    expect.verifySteps([]);
});

test("next_form creates a record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args);
    });
    await mountView({ resModel: "partner", type: "form", arch });
    expect(".o_field_widget[name=name] input").toHaveValue("");
    await contains(".o_field_widget[name=name] input").edit("new partner");
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect.verifySteps([[[], { name: "new partner" }]]);
    expect(".o_form_button_save").toHaveCount(0);
});

test("next_form discards a new record", async () => {
    await mountView({ resModel: "partner", type: "form", arch });
    await contains(".o_field_widget[name=name] input").edit("new partner");
    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=name] input").toHaveValue("");
});
