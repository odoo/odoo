import { after, beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { queryAllProperties, queryAllTexts, queryOne, queryRect, resize } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    pagerNext,
    removeFacet,
    serverState,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
} from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { resetDateFieldWidths } from "@web/views/list/column_width_hook";

describe.current.tags("desktop");

const { ResCompany, ResPartner, ResUsers } = webModels;

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    date = fields.Date();
    datetime = fields.Datetime();
    int_field = fields.Integer();
    qux = fields.Float();
    m2o = fields.Many2one({ relation: "bar" });
    o2m = fields.One2many({ relation: "bar" });
    foo_o2m = fields.One2many({ relation: "foo" });
    m2m = fields.Many2many({ relation: "bar" });
    text = fields.Text();
    amount = fields.Monetary({ currency_field: "currency_id" });
    currency_id = fields.Many2one({ relation: "res.currency", default: 1 });
    reference = fields.Reference({
        selection: [
            ["bar", "Bar"],
            ["res.currency", "Currency"],
        ],
    });

    _records = [
        {
            id: 1,
            foo: "yop",
            bar: true,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            int_field: 10,
            qux: 0.4,
            m2o: 1,
            m2m: [1, 2],
            amount: 1200,
            currency_id: 2,
            reference: "bar,1",
        },
        {
            id: 2,
            foo: "blip",
            bar: true,
            int_field: 9,
            qux: 13,
            m2o: 2,
            m2m: [1, 2, 3],
            amount: 500,
            reference: "res.currency,1",
        },
        {
            id: 3,
            foo: "gnap",
            bar: true,
            int_field: 17,
            qux: -3,
            m2o: 1,
            m2m: [],
            amount: 300,
            reference: "res.currency,2",
        },
        {
            id: 4,
            foo: "blip",
            bar: false,
            int_field: -4,
            qux: 9,
            m2o: 1,
            m2m: [1],
            amount: 0,
        },
    ];
}

class Bar extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Value 1" },
        { id: 2, name: "Value 2" },
        { id: 3, name: "Value 3" },
    ];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char();
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
    ];
}

defineModels([Foo, Bar, Currency, ResCompany, ResPartner, ResUsers]);

beforeEach(() => {
    resize({ width: 800 });
    document.body.style.fontFamily = "sans-serif";
});

function getColumnWidths(root) {
    return queryAllProperties(".o_list_table thead th", "offsetWidth", { root });
}

// width computation
test(`width computation: no record, lot of fields`, async () => {
    Foo._records = [];
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="m2o"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 89, 80, 89, 102, 83, 144, 114, 100]);
});

test(`width computation: no record, few fields`, async () => {
    Foo._records = [];
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 109, 559, 91]);
});

test(`width computation: no record, all fields with a max width`, async () => {
    Foo._records = [];
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="int_field"/>
                <field name="qux"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 262, 233, 266]);
});

test(`width computation: no record, sample data`, async () => {
    Foo._records = [];
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list sample="1">
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
                <field name="m2o"/>
                <field name="int_field"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 109, 186, 186, 186, 91]);
});

test(`width computation: with records, lot of fields`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="m2o"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 89, 80, 89, 102, 83, 144, 114, 100]);
});

test(`width computation: with records, lot of fields, grouped`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="m2o"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id" width="25px"/>
            </list>
        `,
        groupBy: ["int_field"],
    });
    expect(`.o_resize`).toHaveCount(9);
    expect(getColumnWidths()).toEqual([40, 29, 89, 80, 89, 102, 83, 144, 114, 45]);
});

test(`width computation: with records, few fields`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 109, 559, 91]);
});

test(`width computation: with records, no relative fields`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 203, 174, 196, 188]);
});

test(`width computation: with records, very long text field`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, " +
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
        "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
        "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
        "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
        "sunt in culpa qui officia deserunt mollit anim id est laborum";

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="text"/>
                <field name="qux"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 618, 113]);
});

test(`width computation: with records, lot of fields, long texts`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt";
    Foo._records[1].foo = "Duis aute irure dolor in reprehenderit in voluptate velit esse cillumt";

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="text"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 89, 80, 102, 83, 89, 144, 114, 100]);
});

test(`width computation: editable list, overflowing table`, async () => {
    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    // Just want to make sure that the table is overflowed
                    `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                    Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                    Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                    velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                    ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                    Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                    Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                    eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                    nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                    efficitur aliquet.`,
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "abc",
        type: "list",
        arch: `
            <list editable="top">
                <field name="titi"/>
                <field name="grosminet" widget="char"/>
            </list>
        `,
    });
    expect(`table`).toHaveRect(queryRect`.o_list_renderer`, {
        message: "Table should not be stretched by its content",
    });
    expect(getColumnWidths()).toEqual([40, 89, 671]);
});

test(`width computation: with records, few fields, long texts`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt. Duis aute irure dolor in reprehenderit in voluptate velit esse cillumt";
    Foo._records[1].foo =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt. Duis aute irure dolor in reprehenderit in voluptate velit esse cillumt";

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 354, 377]);
});

test(`width computation: list with handle field`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="int_field" widget="handle"/>
                <field name="foo"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 29, 731]);
});

test(`width computation: editable list, no record, with handle field`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="int_field" widget="handle"/>
                <field name="currency_id"/>
                <field name="m2o"/>
            </list>
        `,
    });
    expect(`thead th`).toHaveCount(4, { message: "there should be 4 th" });
    expect(`thead th:eq(0)`).toHaveClass("o_list_record_selector");
    expect(`thead th:eq(1)`).toHaveClass("o_handle_cell");
    expect(`thead th:eq(0)`).toHaveText("", {
        message: "the handle field shouldn't have a header description",
    });
    expect(getColumnWidths()).toEqual([40, 29, 360, 371]);
});

test(`width computation: widget with listViewWidth in its definition`, async () => {
    class MyWidget extends Component {
        static template = xml`<span>My custom widget</span>`;
        static props = ["*"];
    }
    const myWidget = {
        listViewWidth: 171,
        component: MyWidget,
    };
    registry.category("view_widgets").add("my_widget", myWidget);
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <widget name="my_widget"/>
                <field name="foo"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 180, 580]);
});

test(`width computation: list with width attribute in arch`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="int_field" width="52px"/>
                <field name="foo" width="63px"/>
                <field name="qux"/>
                <field name="currency_id"/>
            </list>`,
    });
    expect(getColumnWidths()).toEqual([40, 61, 72, 102, 524]);
});

test(`width computation: date and datetime with fancy formats`, async () => {
    defineParams({
        lang_parameters: {
            date_format: "%a, %d %B %Y",
            time_format: "%H:%M:%S %p",
        },
    });
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="foo"/>
                <field name="date"/>
                <field name="datetime"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual([
        "yop",
        "Wed, 25 January 2017",
        "Mon, 12 December 2016 11:55:05 AM",
    ]);
    expect(getColumnWidths()).toEqual([40, 307, 177, 276]);
});

test(`width computation: date and datetime with fancy formats (2)`, async () => {
    // Those formats contains static parts ("a" not prefixed by "%") which will be escaped when
    // converted into the luxon format (wrapped into single quotes). The regex that detects patterns
    // like "MMM" (abrev. month, in letters) must properly ignore those escaped parts. This test
    // ensures it.
    defineParams({
        lang_parameters: {
            date_format: "%Ya%ba%d",
            time_format: "%H%M%Sa%p",
        },
    });
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="foo"/>
                <field name="date"/>
                <field name="datetime"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual([
        "yop",
        "2017aJana25",
        "2016aDeca12 115505aAM",
    ]);
    expect(getColumnWidths()).toEqual([40, 459, 103, 198]);
});

test(`width computation: width attribute in arch and overflowing table`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, " +
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
        "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
        "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
        "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
        "sunt in culpa qui officia deserunt mollit anim id est laborum";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="datetime"/>
                <field name="int_field" width="200px"/>
                <field name="text"/>
            </list>
        `,
    });
    expect(getColumnWidths()).toEqual([40, 144, 210, 406]);
});

test(`width computation: no record, nameless and stringless buttons`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button string="choucroute"/>
                <button icon="fa-heart"/>
            </list>
        `,
    });
    const columnWidths = getColumnWidths();
    expect(columnWidths[0]).toBe(40);
    expect(columnWidths[1]).toBeGreaterThan(300);
    expect(columnWidths[2]).toBeGreaterThan(300);
});

test(`width computation: x2many`, async () => {
    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
        <form>
            <sheet>
                <field name="foo_o2m">
                    <list>
                        <field name="bar"/>
                        <field name="foo"/>
                        <field name="qux"/>
                    </list>
                </field>
            </sheet>
        </form>`,
    });

    const columnWidths = getColumnWidths();
    expect(columnWidths[1]).toBeGreaterThan(380);
});

test(`width computation: x2many, column_invisible`, async () => {
    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <field name="foo_o2m">
                        <list>
                            <field name="bar"/>
                            <field name="int_field" column_invisible="not parent.bar"/>
                            <field name="foo"/>
                            <field name="qux"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    let columnWidths = getColumnWidths();
    const fooWidth = columnWidths[1];
    expect(fooWidth).toBeGreaterThan(380);

    await contains(".o_field_widget[name=bar] input").click();
    columnWidths = getColumnWidths();
    expect(columnWidths[2]).toBeLessThan(fooWidth);
    expect(columnWidths[2]).toBeGreaterThan(220);
});

test(`width computation: x2many, editable list, initially invisible, overflowing`, async () => {
    Foo._fields.o2m = fields.One2many({ relation: "abc" });
    Foo._records = [{ id: 1, o2m: [1] }];

    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                    "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                    "Vivamus ac lectus velit.",
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Page1"></page>
                        <page string="Page2">
                            <field name="o2m">
                                <list editable="bottom">
                                    <field name="titi"/>
                                    <field name="grosminet"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.nav-item:eq(-1) .nav-link`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    const columnWidths = getColumnWidths();
    expect(columnWidths[1]).toBeGreaterThan(500);
});

test(`width computation: x2many, editable list, with invisible modifier on x2many`, async () => {
    Foo._fields.o2m = fields.One2many({ relation: "abc" });
    Foo._records = [{ id: 1, bar: true, o2m: [1] }];
    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                    "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                    "Vivamus ac lectus velit.",
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <field name="o2m" invisible="bar">
                        <list editable="bottom">
                            <field name="titi"/>
                            <field name="grosminet"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    const columnWidths = getColumnWidths();
    expect(columnWidths[1]).toBeGreaterThan(500);
});

test(`width computation: widths are re-computed on window resize`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
        "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
        "ipsum purus bibendum est.";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field"/>
                <field name="text"/>
            </list>
        `,
    });

    expect(getColumnWidths()).toEqual([40, 80, 680]);

    resize({ width: queryRect(getFixture()).width * 1.2 });
    await runAllTimers();
    expect(getColumnWidths()).toEqual([40, 80, 840]);
});

test(`width computation: widths are re-computed on parent resize`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
        "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
        "ipsum purus bibendum est.";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field"/>
                <field name="text"/>
            </list>
        `,
    });

    expect(getColumnWidths()).toEqual([40, 80, 680]);

    queryOne(".o_list_renderer").style.width = "600px";
    await runAllTimers();
    expect(getColumnWidths()).toEqual([40, 80, 480]);
});

test(`width computation: button columns don't have a max width`, async () => {
    // set a long foo value s.t. the column can be squeezed
    Foo._records[0].foo = "Lorem ipsum dolor sit amet";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button name="b1" string="Do This"/>
                <button name="b2" string="Do That"/>
                <button name="b3" string="Or Rather Do Something Else"/>
            </list>
        `,
    });

    expect(queryAllProperties(".o_list_table", "offsetWidth")[0]).toBe(800);
    let columnWidths = getColumnWidths();
    expect(columnWidths[1]).toBeGreaterThan(130);
    expect(columnWidths[2]).toBeGreaterThan(330);

    // simulate a window resize (buttons column width should not be squeezed)
    await resize({ width: 300 });
    await runAllTimers();
    await animationFrame();
    const tableWidth = queryAllProperties(".o_list_table", "offsetWidth")[0];
    expect(tableWidth).toBeGreaterThan(300);
    expect(tableWidth).toBeLessThan(800);
    columnWidths = getColumnWidths();
    // indices 0 and 1 because selectors aren't displayed on small screens
    expect(columnWidths[0]).toBe(100);
    expect(columnWidths[1]).toBeGreaterThan(330);
});

test(`width computation: button with width in arch`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button string="choucroute"/>
                <button icon="fa-heart" width="25px"/>
                <button icon="fa-cog" width="59px"/>
                <button icon="fa-list"/>
                <button icon="fa-play"/>
            </list>
        `,
    });

    expect(getColumnWidths()).toEqual([40, 216, 216, 34, 68, 227]);
});

// freeze column widths
test(`freeze widths: add first record`, async () => {
    Foo._records = []; // in this scenario, we start with no records

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="datetime"/>
                <field name="text"/>
            </list>
        `,
    });

    const initialWidths = getColumnWidths();
    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: edit a record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="datetime"/>
                <field name="text"/>
                <field name="foo"/>
            </list>
        `,
    });

    const initialWidths = getColumnWidths();
    await contains(`.o_data_row:eq(0) > .o_data_cell:eq(1)`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    const longVal =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
        "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
        "ipsum purus bibendum est.";
    await contains(`.o_field_widget[name=text] .o_input`).edit(longVal, { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: switch records in edition`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="text"/>
            </list>
        `,
    });

    const initialWidths = getColumnWidths();
    await contains(`.o_data_row:eq(0) > .o_data_cell:eq(1)`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(getColumnWidths()).toEqual(initialWidths);

    await contains(`.o_data_row:eq(1) > .o_data_cell:eq(1)`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: switch mode`, async () => {
    // Warning: this test is css dependant
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
    });
    const startWidths = getColumnWidths();
    const startWidth = queryRect(`table`).width;

    // start edition of first row
    await contains(`td:not(.o_list_record_selector)`).click();
    const editionWidths = getColumnWidths();
    const editionWidth = queryRect(`table`).width;

    // leave edition
    await contains(`.o_list_button_save`).click();
    const readonlyWidths = getColumnWidths();
    const readonlyWidth = queryRect(`table`).width;
    expect(editionWidth).toBe(startWidth, {
        message: "table should have kept the same width when switching from readonly to edit mode",
    });
    expect(editionWidths).toEqual(startWidths, {
        message:
            "width of columns should remain unchanged when switching from readonly to edit mode",
    });
    expect(readonlyWidth).toBe(editionWidth, {
        message: "table should have kept the same width when switching from edit to readonly mode",
    });
    expect(readonlyWidths).toEqual(editionWidths, {
        message:
            "width of columns should remain unchanged when switching from edit to readonly mode",
    });
});

test(`freeze widths: switch mode (lot of fields)`, async () => {
    // Warning: this test is css dependant
    serverState.multiLang = true;

    Foo._fields.foo = fields.Char({ translate: true });
    Foo._fields.boolean = fields.Boolean();

    // the width is hardcoded to make sure we have the same condition
    // between debug mode and non debug mode
    await resize({ width: 1200 });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" required="1"/>
                <field name="int_field" readonly="1"/>
                <field name="boolean"/>
                <field name="date"/>
                <field name="text"/>
                <field name="amount"/>
                <field name="currency_id" column_invisible="1"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
    });
    const startHeight = queryRect(`.o_data_row:eq(0)`).height;
    const startWidth = queryRect(`.o_data_row:eq(0)`).width;

    // start edition of first row
    await contains(`.o_data_row > td:not(.o_list_record_selector)`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    const editionHeight = queryRect(`.o_data_row:eq(0)`).height;
    const editionWidth = queryRect(`.o_data_row:eq(0)`).width;

    // leave edition
    await contains(`.o_list_button_save`).click();
    const readonlyHeight = queryRect(`.o_data_row:eq(0)`).height;
    const readonlyWidth = queryRect(`.o_data_row:eq(0)`).width;
    expect(startHeight).toBe(editionHeight);
    expect(startHeight).toBe(readonlyHeight);
    expect(startWidth).toBe(editionWidth);
    expect(startWidth).toBe(readonlyWidth);
});

test(`freeze widths: navigate with the pager`, async () => {
    Foo._records[0].foo = "Some very very long value for a char field";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
            </list>
        `,
        limit: 2,
    });

    const initialWidths = getColumnWidths();
    await pagerNext();
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: toggle a filter`, async () => {
    Foo._records[0].foo = "Some very very long value for a char field";
    Foo._records[3].text = "Some very very long value for a char field";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        searchViewArch: `
            <search>
                <filter string="My Filter" name="my_filter" domain="[['id', '>', 2]]"/>
            </search>
        `,
        limit: 2,
    });

    const initialWidths = getColumnWidths();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: empty list, remove a filter s.t. records appear`, async () => {
    Foo._records[0].foo = "Some very very long value for a char field";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        searchViewArch: `
            <search>
                <filter string="My Filter" name="my_filter" domain="[['id', '=', 0]]"/>
            </search>
        `,
        context: {
            search_default_my_filter: true,
        },
    });

    expect(".o_data_row").toHaveCount(0);

    const initialWidths = getColumnWidths();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(".o_data_row").toHaveCount(4);
    expect(getColumnWidths()).not.toEqual(initialWidths);
});

test(`freeze widths: grouped list, open a group`, async () => {
    Foo._records[3].foo = "Some very very long value for a char field";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        groupBy: ["bar"],
    });

    expect(".o_data_row").toHaveCount(0);

    const initialWidths = getColumnWidths();
    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(1);
    expect(getColumnWidths()).not.toEqual(initialWidths);
});

test(`freeze widths: toggle a filter, vertical scrollbar appears`, async () => {
    await resize({ height: 500 });

    for (let i = 10; i < 20; i++) {
        Foo._records.push({ id: i, bar: true, foo: `Foo ${i}` });
    }
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="foo"/>
            </list>
        `,
        searchViewArch: `
            <search>
                <filter string="My Filter" name="my_filter" domain="[['id', '>', 16]]"/>
            </search>
        `,
        context: {
            search_default_my_filter: true,
        },
    });

    expect(".o_data_row").toHaveCount(3);
    const renderer = queryOne(".o_list_renderer");
    expect(renderer.scrollHeight).toBe(renderer.clientHeight);

    await removeFacet("My Filter");
    expect(".o_data_row").toHaveCount(14);
    expect(renderer.scrollHeight).toBeGreaterThan(renderer.clientHeight); // there must be a vertical scrollbar
    expect(renderer.scrollWidth).toBe(renderer.clientWidth); // there must be no horizontal scrollbar
});

test(`freeze widths: add a record in empty list`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="bar"/>
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        noContentHelp: '<p class="hello">click to add a foo</p>',
    });
    expect(`.o_view_nocontent`).toHaveCount(1, { message: "should have no content help" });
    const initialWidths = getColumnWidths();

    // click on create button
    await contains(`.o_list_button_add`).click();
    expect(getColumnWidths()).toEqual(initialWidths);

    // creating one record
    await contains(`.o_selected_row [name='foo'] input`).edit(
        "Some very very long value for a char field",
        { confirm: false }
    );
    await contains(`.o_list_button_save`).click();
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: add a record in empty list with handle widget`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="int_field" widget="handle"/>
                <field name="foo"/>
            </list>
        `,
        noContentHelp: '<p class="hello">click to add a foo</p>',
    });
    expect(`.o_view_nocontent`).toHaveCount(1, { message: "should have no content help" });
    const initialWidths = getColumnWidths();

    // click on create button
    await contains(`.o_list_button_add`).click();
    expect(getColumnWidths()).toEqual(initialWidths);

    // creating one record
    await contains(`.o_selected_row [name='foo'] input`).edit("test_foo", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: edit multiple records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="datetime"/>
                <field name="text"/>
            </list>
        `,
    });

    const initialWidths = getColumnWidths();

    // select two records and edit
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    const longVal =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
        "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus " +
        "bibendum est.";
    await contains(`.o_field_widget[name=text] textarea`).edit(longVal);
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .btn-primary`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: toggle optional fields`, async () => {
    Foo._records[0].foo = "Lorem ipsum dolor sit amet, consectetur adipiscing elit.";
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="date"/>
                <field name="text"/>
                <field name="qux" optional="hide"/>
                <field name="datetime" optional="show"/>
                <field name="foo" optional="hide"/>
            </list>
        `,
    });

    expect(getColumnWidths()).toEqual([40, 83, 500, 144, 32]);

    await contains(".o_optional_columns_dropdown_toggle").click();
    await contains(".dropdown-item input:eq(0)").click();
    expect(getColumnWidths()).toEqual([40, 83, 397, 102, 145, 32]);

    await contains(".dropdown-item input:eq(1)").click();
    expect(getColumnWidths()).toEqual([40, 83, 542, 102, 32]);

    await contains(".dropdown-item input:eq(2)").click();
    expect(getColumnWidths()).toEqual([40, 83, 89, 102, 453, 32]);

    await contains(".dropdown-item input:eq(1)").click();
    expect(getColumnWidths()).toEqual([40, 83, 89, 103, 145, 308, 32]);
});

test(`freeze widths: x2many, add first record`, async () => {
    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
            <form>
                <field name="foo_o2m">
                    <list editable="top">
                        <field name="date"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
    });

    const initialWidths = getColumnWidths();
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(1);
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: x2many, edit a record`, async () => {
    Foo._records[0].foo_o2m = [2];

    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
            <form>
                <field name="foo_o2m">
                    <list editable="top">
                        <field name="date"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        mode: "edit",
    });

    const initialWidths = getColumnWidths();
    await contains(".o_data_row .o_data_cell").click();
    expect(getColumnWidths()).toEqual(initialWidths);

    const longVal =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
        "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum " +
        "purus bibendum est.";
    await contains(".o_field_widget[name=foo] input").edit(longVal);
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: x2many, remove last record`, async () => {
    Foo._records[0].foo_o2m = [2];

    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
            <form>
                <field name="foo_o2m">
                    <list editable="top">
                        <field name="date"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        mode: "edit",
    });

    const initialWidths = getColumnWidths();
    await contains(".o_data_row .o_list_record_remove").click();
    expect(getColumnWidths()).toEqual(initialWidths);
});

test(`freeze widths: x2many, toggle optional field`, async () => {
    Foo._records[0].foo_o2m = [2];

    await mountView({
        type: "form",
        resModel: "foo",
        arch: `
            <form>
                <field name="foo_o2m">
                    <list editable="top">
                        <field name="date" required="1"/>
                        <field name="foo"/>
                        <field name="int_field" optional="1"/>
                    </list>
                </field>
            </form>`,
    });

    expect(getColumnWidths()).toEqual([94, 642, 32]);

    // create a record to store the current widths, but discard it directly to keep
    // the list empty (otherwise, the browser automatically computes the optimal widths)
    await contains(".o_field_x2many_list_row_add a").click();
    expect(getColumnWidths()).toEqual([94, 642, 32]);

    await contains(".o_optional_columns_dropdown_toggle").click();
    await contains(".dropdown-item input").click();
    expect(getColumnWidths()).toEqual([94, 561, 80, 32]);
});

// manually resize columns
test(`resize, reorder, resize again`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    const originalWidths = getColumnWidths();
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    let widthsAfterResize = getColumnWidths();
    expect(widthsAfterResize[0]).toBe(originalWidths[0]);
    expect(widthsAfterResize[1]).toBeGreaterThan(originalWidths[1]);

    // 2. Reorder column foo.
    await contains(`th:eq(1)`).click();
    const widthsAfterReorder = getColumnWidths();
    expect(widthsAfterResize[0]).toBe(widthsAfterReorder[0]);
    expect(widthsAfterResize[1]).toBe(widthsAfterReorder[1]);

    // 3. Resize again, this time check sizes while dragging and after drop.
    const { moveTo, drop } = await contains(`th:eq(1) .o_resize`, { visible: false }).drag();
    await moveTo(`th:eq(2)`);
    widthsAfterResize = getColumnWidths();
    expect(widthsAfterResize[1]).toBeGreaterThan(widthsAfterReorder[1]);

    await drop();
    expect(widthsAfterResize[1]).toBeGreaterThan(widthsAfterReorder[1]);
});

test(`resize column and toggle one checkbox`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    const widthsAfterResize = getColumnWidths();

    // 2. Column size should be the same after selecting a row
    await contains(`tbody .o_list_record_selector`).click();
    expect(getColumnWidths()).toEqual(widthsAfterResize, {
        message: "Width must not have been changed after selecting a row",
    });
});

test(`resize column, then resize window`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field"/>
                <field name="foo"/>
            </list>
        `,
    });

    expect(getColumnWidths()).toEqual([40, 80, 680]);

    // Resize column foo to middle of column int_field.
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    expect(getColumnWidths()).toEqual([40, 520, 679]);

    // Resize the window
    resize({ width: 1200 });
    await runAllTimers();
    await animationFrame();
    expect(getColumnWidths()).toEqual([40, 80, 1080]); // all available space should be used again

    // Reduce size of column foo
    await contains(`th:eq(2) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    expect(getColumnWidths()).toEqual([40, 80, 591]);

    // Resize the window
    resize({ width: 1000 });
    await runAllTimers();
    await animationFrame();
    expect(getColumnWidths()).toEqual([40, 80, 880]); // all available space should be used again
});

test(`resize column and toggle check all`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    const widthsAfterResize = getColumnWidths();

    // 2. Column size should be the same after selecting all
    await contains(`thead .o_list_record_selector`).click();
    expect(getColumnWidths()).toEqual(widthsAfterResize, {
        message: "Width must not have been changed after selecting all",
    });
});

test(`resize column headers in editable list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="reference" optional="hide"/>
            </list>
        `,
    });
    const originalWidths = getColumnWidths();
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);

    const finalWidths = getColumnWidths();
    expect(finalWidths[0]).toBe(originalWidths[0]);
    expect(finalWidths[2]).toBe(originalWidths[2]);
});

test.todo(`resize column headers in editable list (2)`, async () => {
    // This test will ensure that, on resize list header,
    // the resized element have the correct size and other elements are not resized
    Foo._records[0].foo = "a".repeat(200);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="bar"/>
                <field name="reference" optional="hide"/>
            </list>
        `,
    });
    const originalWidth1 = queryRect(`th:eq(1)`).width;
    const originalWidth2 = queryRect(`th:eq(2)`).width;

    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2) .o_resize`, {
        visible: false,
    });
    const finalWidth1 = queryRect(`th:eq(1)`).width;
    const finalWidth2 = queryRect(`th:eq(2)`).width;
    expect(
        Math.abs(Math.floor(finalWidth1) - Math.floor(originalWidth1 + originalWidth2))
    ).toBeLessThan(1);
    expect(Math.floor(finalWidth2)).toBe(Math.floor(originalWidth2));
});

test(`resize column with several x2many lists in form group`, async () => {
    Bar._fields.text = fields.Char();
    Foo._records[0].o2m = [1, 2];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="o2m">
                        <list editable="bottom">
                            <field name="display_name"/>
                            <field name="text"/>
                        </list>
                    </field>
                    <field name="m2m">
                        <list editable="bottom">
                            <field name="display_name"/>
                            <field name="text"/>
                        </list>
                    </field>
                </group>
            </form>
        `,
        resId: 1,
    });
    const initialWidth0 = queryRect(`.o_field_x2many_list table:eq(0)`).width;
    const initialWidth1 = queryRect(`.o_field_x2many_list table:eq(1)`).width;
    expect(initialWidth0).toBe(initialWidth1, {
        message: "both table columns have same width",
    });

    await contains(`th:eq(0) .o_resize`, { visible: false }).dragAndDrop(`th:eq(1)`, {
        position: "right",
    });
    expect(`.o_field_x2many_list table:eq(0)`).not.toHaveRect(
        { width: initialWidth0 },
        {
            message: "first o2m table is resized and width of table has changed",
        }
    );
    expect(`.o_field_x2many_list table:eq(1)`).toHaveRect(
        { width: initialWidth1 },
        {
            message: "second o2m table should not be impacted on first o2m in group resized",
        }
    );
});

test(`resize column with x2many list with several fields in form notebook`, async () => {
    Foo._records[0].o2m = [1, 2];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Page 1">
                            <field name="o2m">
                                <list editable="bottom">
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    const listInitialWidth = queryRect(`.o_list_renderer`).width;
    await contains(`th:eq(0) .o_resize`, { visible: false }).dragAndDrop(`th:eq(1)`, {
        position: "right",
    });
    expect(`.o_list_renderer`).toHaveRect(
        { width: listInitialWidth },
        {
            message: "resizing the column should not impact the width of list",
        }
    );
});

test(`resize: unnamed columns cannot be resized`, async () => {
    Foo._records = [{ id: 1, o2m: [1] }];
    Bar._records = [{ id: 1, display_name: "Oui" }];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list editable="top">
                            <field name="display_name"/>
                            <button name="the_button" icon="fa-heart"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
        mode: "edit",
    });
    expect(Math.floor(queryRect(`.o_field_one2many th:eq(0)`).right)).toBe(
        Math.floor(queryRect(`.o_field_one2many th:eq(0) .o_resize`).right),
        {
            message: "First resize handle should be attached at the end of the first header",
        }
    );
    expect(`.o_field_one2many th:eq(1) .o_resize`).toHaveCount(0, {
        message: "Columns without name should not have a resize handle",
    });
});
