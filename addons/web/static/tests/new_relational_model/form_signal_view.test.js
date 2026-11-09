import { expect, queryAllTexts, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onPatched } from "@odoo/owl";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    getPagerValue,
    models,
    mountView,
    onRpc,
    pagerNext,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { FormSignalField } from "@web/new_relational_model/form_signal_field";
import { FormSignalRenderer } from "@web/new_relational_model/form_signal_renderer";

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char({ string: "Foo" });
    int_field = fields.Integer({ string: "Int field" });
    bar = fields.Boolean({ string: "Bar" });
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["done", "Done"],
        ],
        default: "draft",
    });
    product_id = fields.Many2one({ string: "Product", relation: "product" });
    tag_ids = fields.Many2many({ string: "Tags", relation: "tag" });

    _records = [
        {
            id: 1,
            name: "first record",
            foo: "yop",
            int_field: 10,
            bar: true,
            state: "draft",
            product_id: 37,
            tag_ids: [12, 14],
        },
        { id: 2, name: "second record", foo: "blip", int_field: 9, state: "done" },
    ];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [{ id: 37, name: "xphone" }];
}

class Tag extends models.Model {
    name = fields.Char();

    _records = [
        { id: 12, name: "gold" },
        { id: 14, name: "silver" },
    ];
}

defineModels([Partner, Product, Tag]);

const ARCH = /* xml */ `
    <form js_class="form_signal">
        <header>
            <field name="state"/>
        </header>
        <sheet>
            <h1><field name="name"/></h1>
            <group>
                <group>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="bar"/>
                </group>
                <group>
                    <field name="product_id"/>
                    <field name="tag_ids"/>
                </group>
            </group>
            <notebook>
                <page string="Page 1">
                    <div class="page_1">page 1 content</div>
                </page>
                <page string="Page 2" invisible="state == 'done'">
                    <div class="page_2">page 2 content</div>
                </page>
            </notebook>
        </sheet>
    </form>
`;

test("renders a record", async () => {
    await mountView({ resModel: "partner", type: "form", arch: ARCH, resId: 1 });

    expect(".o_form_signal_renderer").toHaveCount(1);
    expect("h1 .o_field_widget[name=name] input").toHaveValue("first record");
    expect(queryAllTexts(".o_inner_group .o_form_label")).toEqual([
        "Foo",
        "Int field",
        "Bar",
        "Product",
        "Tags",
    ]);
    expect(".o_field_widget[name=foo] input").toHaveValue("yop");
    expect(".o_field_widget[name=int_field] input").toHaveValue(10);
    expect(".o_field_widget[name=bar] input").toBeChecked();
    expect(".o_field_widget[name=state] select").toHaveValue("draft");
    expect(".o_field_widget[name=product_id]").toHaveText("xphone");
    expect(".o_field_widget[name=tag_ids]").toHaveText("gold, silver");
    expect(".o_notebook .nav-link").toHaveCount(2);
    expect(".page_1").toHaveCount(1);
    // no changes: no save button
    expect(".o_form_button_save").toHaveCount(0);
});

test("edit, save and discard", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(["web_save", args[0], args[1]]);
    });
    await mountView({ resModel: "partner", type: "form", arch: ARCH, resId: 1 });

    await contains(".o_field_widget[name=foo] input").edit("changed");
    expect(".o_form_button_save").toHaveCount(1);
    await contains(".o_field_widget[name=int_field] input").edit("42");
    await clickSave();
    expect.verifySteps([["web_save", [1], { foo: "changed", int_field: 42 }]]);
    expect(".o_form_button_save").toHaveCount(0);
    expect(".o_field_widget[name=foo] input").toHaveValue("changed");

    await contains(".o_field_widget[name=foo] input").edit("not saved");
    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=foo] input").toHaveValue("changed");
    expect(".o_form_button_save").toHaveCount(0);
    expect.verifySteps([]);
});

test("modifiers are evaluated against the record", async () => {
    await mountView({ resModel: "partner", type: "form", arch: ARCH, resId: 1 });
    await contains(".o_notebook .nav-link:eq(1)").click();
    expect(".page_2").toHaveCount(1);

    await contains(".o_field_widget[name=state] select").select("done");
    expect(".o_notebook .nav-link").toHaveCount(1);
    // the hidden page was active: back to the first visible one
    expect(".page_1").toHaveCount(1);
});

test("editing a field only renders that field", async () => {
    let rendererPatches = 0;
    const fieldPatches = [];
    patchWithCleanup(FormSignalRenderer.prototype, {
        setup() {
            super.setup();
            onPatched(() => rendererPatches++);
        },
    });
    patchWithCleanup(FormSignalField.prototype, {
        setup() {
            super.setup();
            onPatched(() => fieldPatches.push(this.props.name));
        },
    });
    await mountView({ resModel: "partner", type: "form", arch: ARCH, resId: 1 });

    await contains(".o_field_widget[name=foo] input").edit("changed");
    expect([...new Set(fieldPatches)]).toEqual(["foo"]);
    expect(rendererPatches).toBe(0);

    // `state` is used by a modifier: the renderer renders again
    await contains(".o_field_widget[name=state] select").select("done");
    expect(rendererPatches).toBe(1);
});

test("create a record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(["web_save", args[0], args[1]]);
    });
    await mountView({ resModel: "partner", type: "form", arch: ARCH });

    // default values, from onchange
    expect(".o_field_widget[name=state] select").toHaveValue("draft");
    expect(".o_field_widget[name=foo] input").toHaveValue("");
    expect(".o_form_button_save").toHaveCount(1);
    expect(".o_pager").toHaveCount(0);

    await contains(".o_field_widget[name=name] input").edit("new record");
    await clickSave();
    expect.verifySteps([
        [
            "web_save",
            [],
            {
                name: "new record",
                foo: false,
                int_field: 0,
                bar: false,
                state: "draft",
                product_id: false,
                // x2many default values are not supported yet
            },
        ],
    ]);
    expect(".o_form_button_save").toHaveCount(0);
    expect(getPagerValue()).toEqual([1]);
});

test("the pager saves before moving to the next record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(["web_save", args[0], args[1]]);
    });
    await mountView({ resModel: "partner", type: "form", arch: ARCH, resId: 1, resIds: [1, 2] });
    expect(getPagerValue()).toEqual([1]);

    await contains(".o_field_widget[name=foo] input").edit("changed");
    await pagerNext();
    await animationFrame();
    expect.verifySteps([["web_save", [1], { foo: "changed" }]]);
    expect(getPagerValue()).toEqual([2]);
    expect(".o_field_widget[name=name] input").toHaveValue("second record");
    expect(".o_notebook .nav-link").toHaveCount(1);
});
