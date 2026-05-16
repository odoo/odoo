import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts, queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    editSelectMenu,
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
            name: "xphone",
        },
        {
            id: 41,
            name: "xpad",
        },
    ];
}
class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
defineModels([Partner, Product, User]);

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
    expect(queryOne(".o_select_menu input", { root: td })).toHaveCount(1, {
        message: "td should have a child 'select'",
    });
    expect(td.children).toHaveCount(1, { message: "select tag should be only child of td" });
});

test.tags("desktop");
test("SelectionField in a list view with multi_edit", async () => {
    Partner._records.forEach((r) => (r.color = "red"));
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list string="Colors" multi_edit="1"><field name="color"/></list>',
    });
    // select two records and edit them
    await click(".o_data_row:eq(0) .o_list_record_selector input:first");
    await animationFrame();
    await click(".o_data_row:eq(1) .o_list_record_selector input:first");
    await animationFrame();

    await contains(".o_field_cell[name='color']").click();
    await editSelectMenu(".o_field_widget[name='color'] input", { value: "" });
    await contains(".o_dialog footer button").click();
    expect(queryAllTexts(".o_field_cell")).toEqual(["", "", "Red"]);

    await contains(".o_field_cell[name='color']").click();
    await editSelectMenu(".o_field_widget[name='color'] input", { value: "Black" });
    await contains(".o_dialog footer button").click();
    expect(queryAllTexts(".o_field_cell")).toEqual(["Black", "Black", "Red"]);
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
    expect(".o_select_menu").toHaveCount(3);
    await contains(".o_field_widget[name='product_id'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["xphone", "xpad"]);
    expect(".o_field_widget[name='product_id'] input").toHaveValue("xphone");
    expect(".o_field_widget[name='trululu'] input").toHaveValue("");
    await editSelectMenu(".o_field_widget[name='product_id'] input", { value: "xpad" });
    expect(".o_field_widget[name='color'] input").toHaveValue("Red");
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

    await editSelectMenu(".o_field_widget[name='trululu'] input", { value: "" });
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

    await contains(".o_field_widget[name='trululu'] input").click();
    expect(".o_select_menu_item:contains(<span>hey</span>)").toHaveCount(1);
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

    await contains(".o_field_widget[name='feedback_value'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Good", "Bad"]);

    // change value to update widget modifier values
    await editSelectMenu(".o_field_widget[name='feedback_value'] input", { value: "Bad" });
    await contains(".o_field_widget[name='color'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Red", "Black"]);
});

test("selection field with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="trululu" widget="selection" placeholder="Placeholder"/></form>`,
    });

    expect(`.o_field_widget[name='trululu'] input`).toHaveAttribute("placeholder", "Placeholder");
});

test("placeholder_field shows as placeholder", async () => {
    Partner._fields.char = fields.Char({
        default: "My Placeholder",
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <field name="trululu" widget="selection" options="{'placeholder_field' : 'char'}"/>
            <field name="char"/>
        </form>`,
    });
    expect(`.o_field_widget[name='trululu'] input`).toHaveAttribute(
        "placeholder",
        "My Placeholder"
    );
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

    await contains(".o_field_widget[name='color'] input").click();
    expect(".o_select_menu_item").toHaveCount(2, {
        message: "Two options are displayed",
    });
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Red", "Black"]);
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
    await editSelectMenu(".o_field_widget[name='color'] input", { value: "Black" });
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

    await contains(".o_field_widget[name='color'] input").click();
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

test.tags("mobile");
test("SelectionField search is disabled in BottomSheet", async function (assert) {
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

    await contains(".o_field_widget[name='color'] input").click();
    expect(".o_bottom_sheet input").toHaveCount(0);
});
