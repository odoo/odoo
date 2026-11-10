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

    _records = [
        { id: 1, name: "first record", parent_id: 2 },
        { id: 2, name: "second record" },
    ];
}

defineModels([Partner]);

const arch = `
    <form js_class="form_signal">
        <field name="name"/>
        <field name="parent_id"/>
    </form>`;

test("form_signal displays a record", async () => {
    await mountView({ resModel: "partner", type: "form", arch, resId: 1 });
    expect("input[name=name]").toHaveValue("first record");
    expect("span[name=parent_id]").toHaveText("second record");
    expect(".o_form_button_save").toHaveCount(0);
});

test("form_signal saves the changes", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args);
    });
    await mountView({ resModel: "partner", type: "form", arch, resId: 1 });
    await contains("input[name=name]").edit("changed");
    expect(".o_form_button_save").toHaveCount(1);

    await contains(".o_form_button_save").click();
    await animationFrame();
    expect.verifySteps([[[1], { name: "changed" }]]);
    expect("input[name=name]").toHaveValue("changed");
    expect(".o_form_button_save").toHaveCount(0);
});

test("form_signal creates a record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args);
    });
    await mountView({ resModel: "partner", type: "form", arch });
    expect("input[name=name]").toHaveValue("");
    await contains("input[name=name]").edit("new partner");
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect.verifySteps([[[], { name: "new partner" }]]);
    expect(".o_form_button_save").toHaveCount(0);
});
