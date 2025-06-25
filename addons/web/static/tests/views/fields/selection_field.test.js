import { expect, test } from "@odoo/hoot";
import {
    click,
    pointerDown,
    queryAll,
    queryAllValues,
    queryFirst,
    queryOne,
    select,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    display_name = fields.Char({ string: "Displayed name" });
    int_field = fields.Integer({ string: "int_field" });
    trululu = fields.Many2one({ string: "Trululu", relation: "partner" });
    product_id = fields.Many2one({ string: "Product", relation: "product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
        string: "Color",
    });
    _records = [
        {
            id: 1,
            display_name: "first record",
            int_field: 10,
            trululu: 4,
        },
        {
            id: 2,
            display_name: "second record",
            int_field: 9,
            trululu: 1,
            product_id: 37,
        },
        {
            id: 4,
            display_name: "aaa",
        },
    ];
}

class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });
    _records = [
        {
            id: 37,
            display_name: "xphone",
        },
        {
            id: 41,
            display_name: "xpad",
        },
    ];
}
defineModels([Partner, Product]);

test("SelectionField in a list view", async () => {
    Partner._records.forEach((r) => (r.color = "red"));
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list string="Colors" editable="top"><field name="color"/></list>',
    });

    expect(".o_data_row").toHaveCount(3);
    await click(".o_data_cell");
    await animationFrame();
    const td = queryFirst("tbody tr.o_selected_row td:not(.o_list_record_selector)");
    expect(queryOne("select", { root: td })).toHaveCount(1, {
        message: "td should have a child 'select'",
    });
    expect(td.children).toHaveCount(1, { message: "select tag should be only child of td" });
});

test("SelectionField, edition and on many2one field", async () => {
    Partner._onChanges.product_id = () => {};
    Partner._records[0].product_id = 37;
    Partner._records[0].trululu = false;
    onRpc(({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="product_id" widget="selection" />
                <field name="trululu" widget="selection" />
                <field name="color" widget="selection" />
            </form>`,
    });
    expect("select").toHaveCount(3);
    expect(".o_field_widget[name='product_id'] select option[value='37']").toHaveCount(1, {
        message: "should have fetched xphone option",
    });
    expect(".o_field_widget[name='product_id'] select option[value='41']").toHaveCount(1, {
        message: "should have fetched xpad option",
    });
    expect(".o_field_widget[name='product_id'] select").toHaveValue("37", {
        message: "should have correct product_id value",
    });
    expect(".o_field_widget[name='trululu'] select").toHaveValue("false", {
        message: "should not have any value in trululu field",
    });

    await click(".o_field_widget[name='product_id'] select");
    await select("41");
    await animationFrame();

    expect(".o_field_widget[name='product_id'] select").toHaveValue("41", {
        message: "should have a value of xphone",
    });
    expect(".o_field_widget[name='color'] select").toHaveValue('"red"', {
        message: "should have correct value in color field",
    });

    expect.verifySteps(["get_views", "web_read", "name_search", "name_search", "onchange"]);
});

test("unset selection field with 0 as key", async () => {
    // The server doesn't make a distinction between false value (the field
    // is unset), and selection 0, as in that case the value it returns is
    // false. So the client must convert false to value 0 if it exists.
    Partner._fields.selection = fields.Selection({
        selection: [
            [0, "Value O"],
            [1, "Value 1"],
        ],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form edit="0"><field name="selection" /></form>',
    });

    expect(".o_field_widget").toHaveText("Value O", {
        message: "the displayed value should be 'Value O'",
    });
    expect(".o_field_widget").not.toHaveClass("o_field_empty", {
        message: "should not have class o_field_empty",
    });
});

test("unset selection field with string keys", async () => {
    // The server doesn't make a distinction between false value (the field
    // is unset), and selection 0, as in that case the value it returns is
    // false. So the client must convert false to value 0 if it exists. In
    // this test, it doesn't exist as keys are strings.
    Partner._fields.selection = fields.Selection({
        selection: [
            ["0", "Value O"],
            ["1", "Value 1"],
        ],
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form edit="0"><field name="selection" /></form>',
    });

    expect(".o_field_widget").toHaveText("", { message: "there should be no displayed value" });
    expect(".o_field_widget").toHaveClass("o_field_empty", {
        message: "should have class o_field_empty",
    });
});

test("unset selection on a many2one field", async () => {
    expect.assertions(1);
    onRpc("web_save", ({ args }) => {
        expect(args[1].trululu).toBe(false, {
            message: "should send 'false' as trululu value",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form><field name="trululu" widget="selection" /></form>',
    });

    await click(".o_form_view select");
    await select("false");
    await animationFrame();
    await clickSave();
    await animationFrame();
});

test("field selection with many2ones and special characters", async () => {
    // edit the partner with id=4
    Partner._records[2].display_name = "<span>hey</span>";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form><field name="trululu" widget="selection" /></form>',
    });

    expect("select option[value='4']").toHaveText("<span>hey</span>");
});

test("required selection widget should not have blank option", async () => {
    Partner._fields.feedback_value = fields.Selection({
        required: true,
        selection: [
            ["good", "Good"],
            ["bad", "Bad"],
        ],
        default: "good",
        string: "Good",
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <field name="feedback_value" />
                    <field name="color" required="feedback_value == 'bad'" />
                </form>`,
    });

    expect(queryAll(".o_field_widget[name='color'] option").map((n) => n.style.display)).toEqual([
        "",
        "",
        "",
    ]);

    expect(
        queryAll(".o_field_widget[name='feedback_value'] option").map((n) => n.style.display)
    ).toEqual(["none", "", ""]);

    // change value to update widget modifier values
    await click(".o_field_widget[name='feedback_value'] select");
    await select('"bad"');
    await animationFrame();
    expect(queryAll(".o_field_widget[name='color'] option").map((n) => n.style.display)).toEqual([
        "none",
        "",
        "",
    ]);
});

test("required selection widget should have only one blank option", async () => {
    Partner._fields.feedback_value = fields.Selection({
        required: true,
        selection: [
            ["good", "Good"],
            ["bad", "Bad"],
        ],
        default: "good",
        string: "Good",
    });

    Partner._fields.color = fields.Selection({
        selection: [
            [false, ""],
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
        string: "Color",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <field name="feedback_value" />
                    <field name="color" required="feedback_value == 'bad'" />
                </form>`,
    });

    expect(".o_field_widget[name='color'] option").toHaveCount(3, {
        message: "Three options in non required field (one blank option)",
    });

    // change value to update widget modifier values
    await click(".o_field_widget[name='feedback_value'] select");
    await select('"bad"');
    await animationFrame();

    expect(queryAll(".o_field_widget[name='color'] option").map((n) => n.style.display)).toEqual([
        "none",
        "",
        "",
    ]);
});

test("selection field with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="trululu" widget="selection" placeholder="Placeholder"/></form>`,
    });

    expect(".o_field_widget[name='trululu'] select option:first").toHaveText("Placeholder");
    expect(".o_field_widget[name='trululu'] select option:first").toHaveValue("false");
});

test("SelectionField in kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="color" widget="selection" />
                    </t>
                </templates>
            </kanban>`,
        domain: [["id", "=", 1]],
    });

    expect(".o_field_widget[name='color'] select").toHaveCount(1, {
        message: "SelectionKanbanField widget applied to selection field",
    });

    expect(".o_field_widget[name='color'] option").toHaveCount(3, {
        message: "Three options are displayed (one blank option)",
    });

    expect(queryAllValues(".o_field_widget[name='color'] option")).toEqual([
        "false",
        '"red"',
        '"black"',
    ]);
});

test("SelectionField - auto save record in kanban view", async () => {
    onRpc("web_save", ({ method }) => expect.step(method));
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="color" widget="selection" />
                        </t>
                    </templates>
                </kanban>`,
        domain: [["id", "=", 1]],
    });
    await click(".o_field_widget[name='color'] select");
    await select('"black"');
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("SelectionField don't open form view on click in kanban view", async function (assert) {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="color" widget="selection" />
                        </t>
                    </templates>
                </kanban>`,
        domain: [["id", "=", 1]],
        selectRecord: () => {
            expect.step("selectRecord");
        },
    });

    await click(".o_field_widget[name='color'] select");
    await animationFrame();
    expect.verifySteps([]);
});

test("SelectionField is disabled if field readonly", async () => {
    Partner._fields.color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
        string: "Color",
        readonly: true,
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="color" widget="selection" />
                        </t>
                    </templates>
                </kanban>
            `,
        domain: [["id", "=", 1]],
    });

    expect(".o_field_widget[name='color'] span").toHaveCount(1, {
        message: "field should be readonly",
    });
});

test("SelectionField is disabled with a readonly attribute", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="color" widget="selection" readonly="1" />
                        </t>
                    </templates>
                </kanban>
            `,
        domain: [["id", "=", 1]],
    });

    expect(".o_field_widget[name='color'] span").toHaveCount(1, {
        message: "field should be readonly",
    });
});

test("SelectionField in kanban view with handle widget", async () => {
    // When records are draggable, most pointerdown events are default prevented. This test
    // comes with a fix that blacklists "select" elements, i.e. pointerdown events on such
    // elements aren't default prevented, because if they were, the select element can't be
    // opened. The test is a bit artificial but there's no other way to test the scenario, as
    // using editSelect simply triggers a "change" event, which obviously always works.
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="color" widget="selection"/>
                        </t>
                    </templates>
                </kanban>`,
    });

    const events = await pointerDown(".o_kanban_record .o_field_widget[name=color] select");
    await animationFrame();
    expect(events.get("pointerdown").defaultPrevented).toBe(false);
});
