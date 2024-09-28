import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class LunchProduct extends models.Model {
    _name = "lunch.product";

    name = fields.Char();
    is_favorite = fields.Boolean();

    _records = [
        {
            id: 1,
            name: "Product A",
        },
    ];

    _views = {
        "kanban,false": `
            <kanban class="o_kanban_test" edit="0">
                <template>
                    <t t-name="card">
                        <field name="is_favorite" widget="lunch_is_favorite" nolabel="1"/>
                        <field name="name"/>
                    </t>
                </template>
            </kanban>
        `,
    };
}

defineMailModels();
defineModels([LunchProduct]);

test("Check is_favorite field is still editable even if the record/view is in readonly.", async () => {
    onRpc("lunch.product", "web_save", ({ args }) => {
        const [ids, vals] = args;
        expect(ids).toEqual([1]);
        expect(vals).toEqual({ is_favorite: true });
        expect.step("web_save");
    });

    await mountView({
        resModel: "lunch.product",
        type: "kanban",
    });

    expect("div[name=is_favorite] .o_favorite").toHaveCount(1);
    expect.verifySteps([]);
    await click("div[name=is_favorite] .o_favorite");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("Check is_favorite field is readonly if the field is readonly", async () => {
    onRpc("lunch.product", "web_save", () => {
        expect.step("web_save");
    });

    LunchProduct._views["kanban,false"] = LunchProduct._views["kanban,false"].replace(
        'widget="lunch_is_favorite"',
        'widget="lunch_is_favorite" readonly="1"'
    );

    await mountView({
        resModel: "lunch.product",
        type: "kanban",
    });

    expect("div[name=is_favorite] .o_favorite").toHaveCount(1);
    expect.verifySteps([]);
    await click("div[name=is_favorite] .o_favorite");
    await animationFrame();
    expect.verifySteps([]);
});
