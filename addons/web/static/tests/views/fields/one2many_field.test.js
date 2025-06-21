import { expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    getNextFocusableElement,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockTimeZone, runAllTimers } from "@odoo/hoot-mock";

import { onWillDestroy, onWillStart, reactive, useState } from "@odoo/owl";
import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickSave,
    contains,
    defineModels,
    fields,
    getService,
    makeServerError,
    mockService,
    models,
    mountView,
    mountViewInDialog,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    selectFieldDropdownItem,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { Record } from "@web/model/relational_model/record";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    qux = fields.Float({ string: "Qux", digits: [16, 1] });
    p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
    });
    turtles = fields.One2many({
        string: "one2many turtle field",
        relation: "turtle",
        relation_field: "turtle_trululu",
    });
    trululu = fields.Many2one({ relation: "partner" });
    timmy = fields.Many2many({ relation: "partner.type", string: "pokemon" });
    product_id = fields.Many2one({ relation: "product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
    date = fields.Date();
    datetime = fields.Datetime();
    user_id = fields.Many2one({ relation: "res.users" });
    reference = fields.Reference({
        selection: [
            ["product.product", "Product"],
            ["partner.type", "Partner Type"],
            ["partner", "Partner"],
        ],
    });

    _records = [
        {
            id: 1,
            name: "first record",
            bar: true,
            foo: "yop",
            int_field: 10,
            qux: 0.44,
            p: [],
            turtles: [2],
            timmy: [],
            trululu: 4,
            user_id: 17,
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            qux: 13,
            p: [],
            timmy: [],
            trululu: 1,
            product_id: 37,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            user_id: 17,
        },
        {
            id: 4,
            name: "aaa",
            bar: false,
        },
    ];
}

class Product extends models.Model {
    _name = "product";

    name = fields.Char();

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

class PartnerType extends models.Model {
    color = fields.Integer({ string: "Color index" });
    name = fields.Char();

    _records = [
        {
            id: 12,
            name: "gold",
            color: 2,
        },
        {
            id: 14,
            name: "silver",
            color: 5,
        },
    ];
}

class Turtle extends models.Model {
    name = fields.Char();
    turtle_foo = fields.Char();
    turtle_bar = fields.Boolean({ default: true });
    turtle_int = fields.Integer();
    turtle_qux = fields.Float({
        string: "Qux",
        digits: [16, 1],
        required: true,
        default: 1.5,
    });
    turtle_description = fields.Text({ string: "Description" });
    turtle_trululu = fields.Many2one({ relation: "partner" });
    turtle_ref = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner", "Partner"],
        ],
    });
    product_id = fields.Many2one({ relation: "product", required: true });
    partner_ids = fields.Many2many({ relation: "partner" });

    _records = [
        {
            id: 1,
            name: "leonardo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [],
        },
        {
            id: 2,
            name: "donatello",
            turtle_bar: true,
            turtle_foo: "blip",
            turtle_int: 9,
            partner_ids: [2, 4],
        },
        {
            id: 3,
            name: "raphael",
            product_id: 37,
            turtle_bar: false,
            turtle_foo: "kawa",
            turtle_int: 21,
            turtle_qux: 9.8,
            partner_ids: [],
            turtle_ref: "product,37",
        },
    ];
}

class Users extends models.Model {
    _name = "res.users";

    name = fields.Char();
    partner_ids = fields.One2many({ relation: "partner", relation_field: "user_id" });

    has_group() {
        return true;
    }

    _records = [
        {
            id: 17,
            name: "Aline",
            partner_ids: [1, 2],
        },
        {
            id: 19,
            name: "Christine",
        },
    ];
}

defineModels([Partner, PartnerType, Product, Turtle, Users]);

test("New record with a o2m also with 2 new records, ordered, and resequenced", async () => {
    // Needed to have two new records in a single stroke
    Partner._onChanges = {
        foo: function (obj) {
            obj.p = [
                [0, 0, { trululu: false }],
                [0, 0, { trululu: false }],
            ];
        },
    };

    let startAssert = false;
    onRpc((args) => {
        if (startAssert) {
            expect.step(args.method + " " + args.model);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="p">
                    <list editable="bottom" default_order="int_field">
                        <field name="int_field" widget="handle"/>
                        <field name="trululu"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    startAssert = true;

    await contains(".o_control_panel_main_buttons .o_form_button_create").click();

    // change the int_field through drag and drop
    // that way, we'll trigger the sorting and the name read
    // of the lines of "p"
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");

    expect.verifySteps(["onchange partner"]);
});

test.tags("desktop");
test("resequence with NULL value", async () => {
    mockService("action", {
        doActionButton(params) {
            params.onClose();
        },
    });
    Partner._records.push(
        { id: 10, int_field: 1 },
        { id: 11, int_field: 2 },
        { id: 12, int_field: 3 },
        { id: 13 }
    );
    Partner._records[0].p = [10, 11, 12, 13];

    const serverValues = {
        10: 1,
        11: 2,
        12: 3,
        13: false,
    };

    onRpc("web_read", function ({ parent }) {
        const res = parent();
        const getServerValue = (record) =>
            serverValues[record.id] === false ? Number.MAX_SAFE_INTEGER : serverValues[record.id];

        // when sorted, NULL values are last
        res[0].p.sort((a, b) => getServerValue(a) - getServerValue(b));
        return res;
    });

    onRpc("web_save", ({ args }) => {
        args[1].p.forEach(([cmd, id, values]) => {
            serverValues[id] = values.int_field;
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet><div name="button_box">
                    <button name="reload" class="reload" type="object" string="Confirm"/>
                </div></sheet>
                <field name="foo"/>
                <field name="p">
                    <list editable="bottom" default_order="int_field">
                        <field name="int_field" widget="handle"/>
                        <field name="id"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["10", "11", "12", "13"]);

    await contains("tbody tr:nth-child(4) .o_handle_cell").dragAndDrop("tbody tr:nth-child(3)");
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["10", "11", "13", "12"]);

    await contains("button.reload").click();
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["10", "11", "13", "12"]);
});

test.tags("desktop");
test("one2many in a list x2many editable use the right context", async () => {
    onRpc("name_create", (args) => {
        expect.step(`name_create ${args.kwargs.context.my_context}`);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="int_field" widget="handle"/>
                        <field name="trululu" context="{'my_context': 'list'}" />
                    </list>
                    <form>
                        <field name="trululu"  context="{'my_context': 'form'}"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list .o_field_x2many_list_row_add a").click();
    await contains("[name='trululu'] input").edit("new partner");
    await selectFieldDropdownItem("trululu", 'Create "new partner"');

    expect.verifySteps(["name_create list"]);
});

test.tags("desktop");
test("one2many in a list x2many non-editable use the right context", async () => {
    onRpc("name_create", (args) => {
        expect.step(`name_create ${args.kwargs.context.my_context}`);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="int_field" widget="handle"/>
                        <field name="trululu" context="{'my_context': 'list'}" />
                    </list>
                    <form>
                        <field name="trululu"  context="{'my_context': 'form'}"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list .o_field_x2many_list_row_add a").click();
    await contains("[name='trululu'] input").edit("new partner");
    await selectFieldDropdownItem("trululu", 'Create "new partner"');

    expect.verifySteps(["name_create form"]);
});

test("O2M field without relation_field", async () => {
    delete Partner._fields.p.relation_field;

    Partner._records[0].p = [2, 4];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="foo" invisible="1"/>
                        <field name="name" />
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list .o_field_x2many_list_row_add a").click();
    expect(".o_dialog").toHaveCount(1);
});

test("do not send context in unity spec if field is invisible", async () => {
    expect.assertions(1);
    onRpc("web_read", ({ kwargs }) => {
        expect(kwargs.specification).toEqual({
            display_name: {},
            p: {},
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" invisible="1" context="{'x': 2}"/>
            </form>`,
        resId: 1,
    });
});

test("O2M List with pager, decoration and default_order: add and cancel adding", async () => {
    // The decoration on the list implies that its condition will be evaluated
    // against the data of the field (actual records *displayed*)
    // If one data is wrongly formed, it will crash
    // This test adds then cancels a record in a paged, ordered, and decorated list
    // That implies prefetching of records for sorting
    // and evaluation of the decoration against *visible records*

    Partner._records[0].p = [2, 4];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom" limit="1" decoration-muted="foo != False" default_order="name">
                        <field name="foo" invisible="1"/>
                        <field name="name" />
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list .o_field_x2many_list_row_add a").click();

    expect(".o_field_x2many_list .o_data_row").toHaveCount(2);

    expect(queryOne(".o_selected_row")).toBe(queryOne(".o_field_x2many_list .o_data_row:eq(1)"), {
        message: "The selected row should be the new one",
    });

    // Cancel Creation
    await press("escape");
    await animationFrame();
    expect(".o_field_x2many_list .o_data_row").toHaveCount(1);
});

test.tags("desktop");
test("O2M with parented m2o and domain on parent.m2o", async () => {
    expect.assertions(4);

    // Records in an o2m can have a m2o pointing to themselves.
    // In that case, a domain evaluation on that field followed by name_search
    // shouldn't send virtual_ids to the server.

    Turtle._fields.parent_id = fields.Many2one({
        string: "Parent",
        relation: "turtle",
    });
    Turtle._views = {
        form: `
            <form>
                <field name="parent_id"/>
            </form>`,
    };
    onRpc("name_search", ({ kwargs }) => {
        expect(kwargs.args).toEqual([["id", "in", []]]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="parent_id"/>
                    </list>
                    <form>
                        <field name="parent_id" domain="[('id', 'in', parent.turtles)]"/>
                    </form>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await clickFieldDropdown("parent_id");
    await contains(".o_field_widget[name=parent_id] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("parent_id", "Create and edit...");

    await contains(".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save").click();
    await contains(".o_dialog:not(.o_inactive_modal) .o_form_button_save_new").click();

    expect(".o_data_row").toHaveCount(1);

    await contains(".o_field_many2one input").click();
});

test.tags("desktop");
test('O2M with buttons with attr "special" in dialog close the dialog', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="p">
                        <list>
                            <field name="bar"/>
                        </list>
                        <form>
                            <field name="bar"/>
                            <footer>
                                <button special="cancel" data-hotkey="x" string="Cancel" class="btn-secondary"/>
                            </footer>
                        </form>
                    </field>
                </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_dialog").toHaveCount(1);

    expect(".modal .btn").toHaveText("Cancel");

    await contains(".modal .btn").click();
    expect(".o_dialog").toHaveCount(0);
});

test.tags("desktop");
test("O2M modal buttons are disabled on click", async () => {
    // Records in an o2m can have a m2o pointing to themselves.
    // In that case, a domain evaluation on that field followed by name_search
    // shouldn't send virtual_ids to the server

    Turtle._fields.parent_id = fields.Many2one({
        string: "Parent",
        relation: "turtle",
    });
    Turtle._views = {
        form: `
            <form>
                <field name="parent_id"/>
            </form>`,
    };
    const def = new Deferred();
    onRpc("web_save", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="parent_id"/>
                    </list>
                    <form>
                        <field name="parent_id"/>
                    </form>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    await clickFieldDropdown("parent_id");
    await contains(".o_field_widget[name=parent_id] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("parent_id", "Create and edit...");
    await contains(".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save").click();
    expect(".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save").not.toBeEnabled();
    def.resolve();
    await animationFrame();
    // close all dialogs
    await contains(".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save").click();
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(0);
});

test.tags("desktop");
test("clicking twice on a record in a one2many will open it once", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="turtle_foo"/>
            </form>`,
    };

    const def = new Deferred();
    let firstRead = true;
    onRpc("turtle", "web_read", async ({ model }) => {
        expect.step("web_read turtle");
        if (!firstRead) {
            await def;
        }
        firstRead = false;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_data_cell").click();
    await contains(".o_data_cell").click();
    def.resolve();
    await animationFrame();
    expect(".modal").toHaveCount(1);

    await contains(".modal .btn-close").click();
    expect(".modal").toHaveCount(0);

    await contains(".o_data_cell").click();
    expect(".modal").toHaveCount(1);

    expect.verifySteps(["web_read turtle"]);
});

test("resequence a x2m in a form view dialog from another x2m", async () => {
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("write", (args) => {
        expect(Object.keys(args.args[1])).toEqual(["turtles"]);
        expect(args.args[1].turtles).toHaveLength(1);
        expect(args.args[1].turtles[0]).toEqual([
            1,
            2,
            {
                partner_ids: [
                    [1, 2, { int_field: 0 }],
                    [1, 4, { int_field: 1 }],
                ],
            },
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="partner_ids">
                            <list editable="top">
                                <field name="int_field" widget="handle"/>
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(".o_data_cell").click();
    expect(".modal").toHaveCount(1);
    expect(queryAllTexts(".modal [name='name']")).toEqual(["aaa", "second record"]);
    expect.verifySteps(["web_read"]);
    await contains(".modal tr:eq(2) .o_handle_cell").dragAndDrop(".modal [name='name']:eq(0)");
    expect(queryAllTexts(".modal [name='name']")).toEqual(["second record", "aaa"]);
    expect.verifySteps([]);

    await contains(".modal .o_form_button_save").click();
    await clickSave();
    expect.verifySteps(["web_save"]);
});

test("one2many list editable with cell readonly modifier", async () => {
    expect.assertions(3);

    Partner._records[0].p = [2];
    Partner._records[1].turtles = [1, 2];
    onRpc("web_save", (args) => {
        expect(args.args[1].p[0][2]).toEqual(
            { foo: "ff", qux: 99, turtles: [] },
            { message: "The right values should be written" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="turtles" invisible="1"/>
                        <field name="foo" readonly="turtles"/>
                        <field name="qux" readonly="turtles"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_selected_row [name=foo] input").toBeFocused({
        message: "The first input of the line should have the focus",
    });

    // Simulating hitting the 'f' key twice
    await contains(".o_selected_row [name=foo] input").edit("f", { confirm: false });
    await contains(".o_selected_row [name=foo] input").edit("ff", { confirm: false });

    expect(".o_selected_row [name=foo] input").toBeFocused({
        message: "The first input of the line should still have the focus",
    });

    // Simulating a TAB key
    await press("Tab");
    await animationFrame();
    await contains(".o_selected_row [name=qux] input").edit(9, { confirm: false });
    await contains(".o_selected_row [name=qux] input").edit(99);
    await clickSave();
});

test("one2many wait for the onchange of the resequenced finish before save", async () => {
    expect.assertions(2);

    Partner._records[0].p = [1, 2];
    Partner._onChanges = {
        p: function (obj) {
            obj.p = [[1, 2, { qux: 99 }]];
        },
    };
    const def = new Deferred();
    onRpc("onchange", async () => {
        await def;
        expect.step("onchange");
    });
    onRpc("web_save", (args) => {
        expect.step("web_save");
        expect(args.args[1].p).toEqual([
            [1, 1, { int_field: 9 }],
            [1, 2, { int_field: 10, qux: 99 }],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="int_field" widget="handle"/>
                        <field name="foo"/>
                        <field name="qux"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    // Drag and drop the second line in first position
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");
    await clickSave();

    // resolve the onchange promise
    def.resolve();
    await animationFrame();
    expect.verifySteps(["onchange", "web_save"]);
});

test("one2many basic properties", async () => {
    Partner._records[0].p = [2];
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Partner page">
                            <field name="p">
                                <list>
                                    <field name="foo"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect.verifySteps(["get_views", "web_read"]);
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_field_x2many_list_row_add").toHaveAttribute("colspan", "2");
    expect("td.o_list_record_remove").toHaveCount(1);
});

test("transferring class attributes in one2many sub fields", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo" class="hey"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect("td.hey").toHaveCount(1);

    await contains("td.o_data_cell").click();
    expect('td.hey div[name="turtle_foo"] input').toHaveCount(1); // WOWL to check! hey on input?
});

test("one2many with date and datetime", async () => {
    mockTimeZone(+2);
    Partner._records[0].p = [2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Partner page">
                            <field name="p">
                                <list>
                                    <field name="date"/>
                                    <field name="datetime"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect("td:eq(0)").toHaveText("01/25/2017");
    expect("td:eq(1)").toHaveText("12/12/2016 12:55:05");
});

test("rendering with embedded one2many", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="P page">
                            <field name="p">
                                <list>
                                    <field name="foo"/>
                                    <field name="bar"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect("thead th:eq(0)").toHaveText("Foo");
    expect("tbody td:eq(0)").toHaveText("blip");
});

test("use the limit attribute in arch (in field o2m inline list view)", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    onRpc("turtle", (args) => {
        expect(args.args[0]).toEqual([1, 2]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="2">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(2);
});

test.tags("desktop");
test("nested x2manys with inline form, but not list", async () => {
    Turtle._views = { list: `<list><field name="turtle_foo"/></list>` };
    Partner._views = {
        list: `<list><field name="foo"/></list>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <form>
                        <field name="turtle_foo"/>
                        <field name="partner_ids">
                            <form>
                                <field name="foo"/>
                            </form>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_form_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_data_row").toHaveCount(2);
});

test.tags("desktop");
test("use the limit attribute in arch (in field o2m non inline list view)", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    Turtle._views = { list: `<list limit="2"><field name="turtle_foo"/></list>` };
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_read", (args) => {
        expect(args.kwargs.specification).toEqual({
            display_name: {},
            turtles: {
                fields: {
                    turtle_foo: {},
                },
                limit: 2,
                order: "",
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="turtles" widget="one2many"/></form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(2);
    expect.verifySteps(["get_views", "get_views", "web_read"]);
});

test.tags("desktop");
test("one2many with default_order on view not inline", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    Turtle._views = {
        list: `
            <list default_order="turtle_foo">
                <field name="turtle_int"/>
                <field name="turtle_foo"/>
            </list>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Turtles">
                            <field name="turtles" widget="one2many"/>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_field_one2many .o_data_cell")).toEqual([
        "9",
        "blip",
        "21",
        "kawa",
        "0",
        "yop",
    ]);
});

test.tags("desktop");
test("embedded one2many with widget", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="P page">
                            <field name="p">
                                <list>
                                    <field name="int_field" widget="handle"/>
                                    <field name="foo"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect("span.o_row_handle").toHaveCount(1);
});

test.tags("desktop");
test("embedded one2many with handle widget", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    Partner._onChanges = {
        turtles: function () {},
    };
    onRpc("onchange", () => {
        expect.step("onchange");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);

    // Drag and drop the second line in first position
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");

    expect.verifySteps(["onchange"]);

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "yop", "kawa"]);

    await clickSave();

    expect(
        Turtle._records.map((r) => {
            return {
                id: r.id,
                turtle_foo: r.turtle_foo,
                turtle_int: r.turtle_int,
            };
        })
    ).toEqual([
        { id: 1, turtle_foo: "yop", turtle_int: 1 },
        { id: 2, turtle_foo: "blip", turtle_int: 0 },
        { id: 3, turtle_foo: "kawa", turtle_int: 21 },
    ]);

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "yop", "kawa"]);
});

test.tags("desktop");
test("onchange for embedded one2many in a one2many", async () => {
    expect.assertions(3);

    Turtle._fields.partner_ids = fields.One2many({ relation: "partner" });
    Turtle._records[0].partner_ids = [1];
    Partner._records[0].turtles = [1];

    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [
                [
                    1,
                    1,
                    {
                        partner_ids: [[4, 2]],
                    },
                ],
            ];
        },
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual([
            [1, 1, { turtle_foo: "hop", partner_ids: [[4, 2]] }],
        ]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_many2many_tags").toHaveText("first record");

    await contains(".o_data_cell:eq(1)").click();
    await contains(".o_selected_row .o_field_widget[name=turtle_foo] input").edit("hop", {
        confirm: "blur",
    });

    expect(".o_field_many2many_tags").toHaveText("first record\nsecond record");

    await clickSave();
});

test("onchange for embedded one2many in a one2many with a second page", async () => {
    Turtle._fields.partner_ids = fields.One2many({ relation: "partner" });
    Turtle._records[0].partner_ids = [1];
    // we need a second page, so we set two records and only display one per page
    Partner._records[0].turtles = [1, 2];

    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [
                [
                    1,
                    1,
                    {
                        partner_ids: [[4, 2]],
                    },
                ],
                [
                    1,
                    2,
                    {
                        turtle_foo: "blip",
                        partner_ids: [[4, 1]],
                    },
                ],
            ];
        },
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual([
            [1, 1, { turtle_foo: "hop", partner_ids: [[4, 2]] }],
            [
                1,
                2,
                {
                    partner_ids: [[4, 1]],
                    turtle_foo: "blip",
                },
            ],
        ]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="1">
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell:eq(1)").click();
    await contains(".o_selected_row .o_field_widget[name=turtle_foo] input").edit("hop", {
        confirm: "blur",
    });
    await clickSave();
});

test("onchange for embedded one2many in a one2many updated by server", async () => {
    // here we test that after an onchange, the embedded one2many field has
    // been updated by a new list of ids by the server response, to this new
    // list should be correctly sent back at save time
    expect.assertions(3);

    Turtle._fields.partner_ids = fields.One2many({ relation: "partner" });
    Partner._records[0].turtles = [2];
    Turtle._records[1].partner_ids = [2];

    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [
                [
                    1,
                    2,
                    {
                        partner_ids: [[4, 4]],
                    },
                ],
            ];
        },
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual(
            [
                [
                    1,
                    2,
                    {
                        partner_ids: [[4, 4]],
                        turtle_foo: "hop",
                    },
                ],
            ],
            {
                message: "The right values should be written",
            }
        );
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_data_cell.o_many2many_tags_cell .o_tag_badge_text")).toEqual([
        "second record",
    ]);

    await contains(".o_data_cell:eq(1)").click();
    await contains(".o_selected_row [name=turtle_foo] input").edit("hop", {
        confirm: "blur",
    });
    await clickSave();
    expect(queryAllTexts(".o_data_cell.o_many2many_tags_cell .o_tag_badge_text")).toEqual([
        "second record",
        "aaa",
    ]);
});

test("onchange for embedded one2many with handle widget", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    let partnerOnchange = 0;
    Partner._onChanges = {
        turtles: function () {
            partnerOnchange++;
        },
    };
    let turtleOnchange = 0;
    Turtle._onChanges = {
        turtle_int: function () {
            turtleOnchange++;
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);
    // Drag and drop the second line in first position
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "yop", "kawa"]);
    expect(turtleOnchange).toBe(2, { message: "should trigger one onchange per line updated" });
    expect(partnerOnchange).toBe(1, { message: "should trigger only one onchange on the parent" });
});

test("onchange for embedded one2many with handle widget using same sequence", async () => {
    Turtle._records[0].turtle_int = 1;
    Turtle._records[1].turtle_int = 1;
    Turtle._records[2].turtle_int = 1;
    Partner._records[0].turtles = [1, 2, 3];
    let turtleOnchange = 0;
    Turtle._onChanges = {
        turtle_int: function () {
            turtleOnchange++;
        },
    };

    onRpc("write", (args) => {
        expect(args.args[1].turtles).toEqual(
            [
                [1, 2, { turtle_int: 1 }],
                [1, 1, { turtle_int: 2 }],
                [1, 3, { turtle_int: 3 }],
            ],
            {
                message:
                    "should change all lines that have changed (the first one doesn't change because it has the same sequence)",
            }
        );
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);

    // Drag and drop the second line in first position
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "yop", "kawa"]);
    expect(turtleOnchange).toBe(3, { message: "should update all lines" });

    await clickSave();
});

test("onchange for embedded one2many with handle widget (more records)", async () => {
    const ids = [];
    for (let i = 10; i < 50; i++) {
        const id = 10 + i;
        ids.push(id);
        Turtle._records.push({
            id: id,
            turtle_int: 0,
            turtle_foo: "#" + id,
        });
    }
    ids.push(1, 2, 3);
    Partner._records[0].turtles = ids;
    Partner._onChanges = {
        turtles: function (obj) {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains("div[name=turtles] .o_pager_next").click();

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);

    await contains(".o_data_cell.o_list_char").click();
    await contains('.o_list_renderer div[name="turtle_foo"] input').edit("blurp");

    // Drag and drop the third line in second position
    await contains("tbody tr:eq(2) .o_handle_cell").dragAndDrop("tbody tr:eq(1)");

    // need to unselect row...
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blurp", "kawa", "blip"]);

    await clickSave();
    await contains('div[name="turtles"] .o_pager_next').click();

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blurp", "kawa", "blip"]);
});

test("onchange with modifiers for embedded one2many on the second page", async () => {
    const ids = [];
    for (let i = 10; i < 60; i++) {
        const id = 10 + i;
        ids.push(id);
        Turtle._records.push({
            id: id,
            turtle_int: 0,
            turtle_foo: "#" + id,
        });
    }
    ids.push(1, 2, 3);
    Partner._records[0].turtles = ids;
    Partner._onChanges = {
        turtles: function (obj) {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" default_order="turtle_int" limit="10">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                        <field name="turtle_qux" readonly="not turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    const getTurtleFooValues = () => {
        return queryAllTexts(".o_data_cell.o_list_char").join("");
    };

    expect(getTurtleFooValues()).toBe("#20#21#22#23#24#25#26#27#28#29");

    await contains(".o_data_cell.o_list_char").click();
    await contains("div[name=turtle_foo] input").edit("blurp");
    // click outside of the one2many to unselect the row
    await contains(".o_form_view").click();
    expect(getTurtleFooValues()).toBe("blurp#21#22#23#24#25#26#27#28#29");

    // the domain fail if the widget does not use the already loaded data.
    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);
    expect(getTurtleFooValues()).toBe("#20#21#22#23#24#25#26#27#28#29");

    // Drag and drop the third line in second position
    await contains("tbody tr:eq(2) .o_handle_cell").dragAndDrop("tbody tr:eq(1)");
    expect(getTurtleFooValues()).toBe("#20#30#31#32#33#34#35#36#37#38");

    // Drag and drop the third line in second position
    await contains("tbody tr:eq(2) .o_handle_cell").dragAndDrop("tbody tr:eq(1)");
    expect(getTurtleFooValues()).toBe("#20#39#40#41#42#43#44#45#46#47");

    await contains(".o_form_view").click();
    expect(getTurtleFooValues()).toBe("#20#39#40#41#42#43#44#45#46#47");

    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);
    expect(getTurtleFooValues()).toBe("#20#21#22#23#24#25#26#27#28#29");
});

test("onchange followed by edition on the second page", async () => {
    const ids = [];
    for (let i = 1; i < 85; i++) {
        const id = 10 + i;
        ids.push(id);
        Turtle._records.push({
            id: id,
            turtle_int: (id / 3) | 0,
            turtle_foo: "#" + i,
        });
    }
    ids.splice(41, 0, 1, 2, 3);
    Partner._records[0].turtles = ids;
    Partner._onChanges = {
        turtles: function (obj) {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="turtles">
                            <list editable="top" default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name=turtles] .o_pager_next").click();

    await contains(".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell:eq(1)").click();
    await contains('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input').edit(
        "value 1"
    );
    await contains(".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell:eq(2)").click();
    await contains('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input').edit(
        "value 2"
    );

    expect(".o_data_row").toHaveCount(40);
    expect(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char:eq(0)").toHaveText("#39", {
        message: "should display '#39' at the first line",
    });

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(40, {
        message: "should display 39 records and the create line",
    });

    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row", {
        message: "should display the create line in first position",
    });
    expect('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"]').toHaveText("", {
        message: "should be an empty input",
    });
    expect(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char:eq(1)").toHaveText("#39");

    await contains(".o_data_row input").edit("value 3", { confirm: "blur" });

    expect(".o_data_row:eq(0)").toHaveClass(["o_data_row", "o_row_draggable"]);
    expect(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char:eq(1)").toHaveText("#39");

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(40, {
        message: "should display 39 records and the create line",
    });
    expect(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char:eq(1)").toHaveText(
        "value 3"
    );
    expect(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char:eq(2)").toHaveText("#39");
});

test("onchange followed by edition on the second page (part 2)", async () => {
    const ids = [];
    for (let i = 1; i < 85; i++) {
        const id = 10 + i;
        ids.push(id);
        Turtle._records.push({
            id: id,
            turtle_int: (id / 3) | 0,
            turtle_foo: "#" + i,
        });
    }
    ids.splice(41, 0, 1, 2, 3);
    Partner._records[0].turtles = ids;
    Partner._onChanges = {
        turtles: function (obj) {},
    };

    // bottom order

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="turtles">
                            <list editable="bottom" default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name=turtles] .o_pager_next").click();

    await contains(".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell:eq(1)").click();
    await contains('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input').edit(
        "value 1",
        { confirm: "blur" }
    );
    await contains(".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell:eq(2)").click();
    await contains('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input').edit(
        "value 2",
        { confirm: "blur" }
    );

    expect(".o_data_row").toHaveCount(40, { message: "should display 40 records" });
    expect(".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char:eq(0)").toHaveText(
        "#39",
        {
            message: "should display '#39' at the first line",
        }
    );
    expect(".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char:eq(39)").toHaveText(
        "#77",
        { message: "should display '#77' at the last line" }
    );

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(41, {
        message: "should display 41 records and the create line",
    });
    expect(".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char:eq(39)").toHaveText(
        "#77",
        { message: "should display '#77' at the penultimate line" }
    );
    expect(".o_data_row:eq(40)").toHaveClass("o_selected_row", {
        message: "should display the create line in first position",
    });

    await contains('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input').edit(
        "value 3",
        { confirm: "blur" }
    );
    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(42, {
        message: "should display 42 records and the create line",
    });
    expect(".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char:eq(40)").toHaveText(
        "value 3"
    );
    expect(".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char:eq(41)").toHaveText(
        ""
    );
    expect(".o_data_row:eq(41)").toHaveClass("o_selected_row", {
        message: "should display the create line in first position",
    });
});

test("onchange returning a commands 4 for an x2many", async () => {
    Partner._onChanges = {
        foo(obj) {
            obj.turtles = [
                [4, 1],
                [4, 3],
            ];
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);

    // change the value of foo to trigger the onchange
    await contains(".o_field_widget[name=foo] input").edit("some value");
    expect(".o_data_row").toHaveCount(3);
});

test("x2many fields inside x2manys are fetched after an onchange", async () => {
    expect.assertions(5);

    Turtle._records[0].partner_ids = [1];
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [
                [3, 2],
                [4, 1],
                [4, 2],
                [4, 3],
            ];
        },
    };

    onRpc("onchange", (args) => {
        expect(args.args[3]).toEqual({
            // spec
            display_name: {},
            foo: {},
            turtles: {
                fields: {
                    partner_ids: {
                        fields: {
                            display_name: {},
                        },
                    },
                    turtle_foo: {},
                },
                limit: 40,
                order: "",
            },
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                        <field name="turtles">
                            <list>
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_field_widget[name=partner_ids]").toHaveText("second record\naaa");

    // change the value of foo to trigger the onchange
    await contains(".o_field_widget[name=foo] input").edit("some value");

    expect(".o_data_row").toHaveCount(3, {
        message: "there should be three records in the relation",
    });
    expect(".o_data_row .o_field_widget[name=partner_ids]:eq(0)").toHaveText("first record");
});

test("reference fields inside x2manys are fetched after an onchange", async () => {
    expect.assertions(4);

    Turtle._records[1].turtle_ref = "product,41";
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [
                [4, 1],
                [4, 3],
            ];
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                        <field name="turtles">
                            <list>
                                <field name="turtle_foo"/>
                                <field name="turtle_ref" class="ref_field"/>
                                </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts(".ref_field")).toEqual(["xpad"]);

    // change the value of foo to trigger the onchange
    await contains(".o_field_widget[name=foo] input").edit("some value");

    expect(".o_data_row").toHaveCount(3);
    expect(queryAllTexts(".ref_field")).toEqual(["xpad", "", "xphone"]);
});

test.tags("desktop");
test("onchange on one2many containing x2many in form view", async () => {
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [[0, false, { turtle_foo: "new record" }]];
        },
    };
    Partner._views = { list: '<list><field name="foo"/></list>', search: "<search></search>" };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                    <form>
                        <field name="partner_ids">
                            <list editable="top">
                                <field name="foo"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1, {
        message: "the onchange should have created one record in the relation",
    });

    // open the created o2m record in a form view, and add a m2m subrecord
    // in its relation
    await contains(".o_data_row .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(0);

    // add a many2many subrecord
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal").toHaveCount(2, { message: "should have opened a second dialog" });

    // select a many2many subrecord
    await contains(".modal:eq(1) .o_list_view .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_x2m_control_panel .o_pager").toHaveCount(0, {
        message: "m2m pager should be hidden",
    });

    // click on 'Save & Close'
    await contains(".modal-footer .btn-primary").click();

    expect(".modal").toHaveCount(0, { message: "dialog should be closed" });

    // reopen o2m record, and another m2m subrecord in its relation, but
    // discard the changes
    await contains(".o_data_row .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);

    // add another m2m subrecord
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal").toHaveCount(2, { message: "should have opened a second dialog" });

    await contains(".modal:eq(1) .o_list_view .o_data_cell").click();

    expect(".modal").toHaveCount(1, { message: "second dialog should be closed" });
    expect(".modal .o_data_row").toHaveCount(2, {
        message: "there should be two records in the one2many in the dialog",
    });

    // click on 'Discard'
    await contains(".modal-footer .btn-secondary").click();

    expect(".modal").toHaveCount(0, { message: "dialog should be closed" });

    // reopen o2m record to check that second changes have properly been discarded
    await contains(".o_data_row .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);
});

test.tags("desktop");
test("onchange on one2many with x2many in list (no widget) and form view (list)", async () => {
    expect.assertions(7);
    Turtle._fields.turtle_foo = fields.Char({ default: "a default value" });
    Partner._onChanges = {
        foo: function (obj) {
            obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
        },
    };
    onRpc("partner", "onchange", ({ args }) => {
        expect(args[3]).toEqual({
            display_name: {},
            foo: {},
            p: {
                fields: {
                    turtles: {
                        fields: {
                            turtle_foo: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <list>
                            <field name="turtles"/>
                        </list>
                        <form>
                            <field name="turtles">
                                <list editable="top">
                                    <field name="turtle_foo"/>
                                </list>
                            </field>
                        </form>
                    </field>
                </form>`,
    });

    expect(".o_data_row").toHaveCount(1, {
        message: "the onchange should have created one record in the relation",
    });

    // open the created o2m record in a form view
    await contains(".o_data_row .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_data_row").toHaveText("hello");

    // add a one2many subrecord and check if the default value is correctly applied
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal .o_data_row").toHaveCount(2);
    expect(".modal .o_data_row .o_field_widget[name=turtle_foo] input").toHaveValue(
        "a default value"
    );
});

test("save an o2m dialog form view and discard main form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row [name='name']").toHaveText("donatello");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name'] input").toHaveValue("donatello");

    await contains(".modal [name='name'] input").edit("leonardo");
    await contains(".modal .o_form_button_save").click();
    expect(".modal").toHaveCount(0);
    expect(".o_data_row [name='name']").toHaveText("leonardo");

    await contains(".o_data_row .o_data_cell").click();
    await contains(".modal .o_form_button_cancel").click();
    expect(".o_data_row [name='name']").toHaveText("leonardo");

    await contains(".o_form_button_cancel").click();
    expect(".o_data_row [name='name']").toHaveText("donatello");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name'] input").toHaveValue("donatello");
});

test("discard with nested o2m form view dialog", async () => {
    Partner._records[0].p = [2];
    Partner._records[1].p = [4];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="name"/>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <field name="p">
                            <list>
                                <field name="name"/>
                            </list>
                            <form>
                                <field name="name"/>
                            </form>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row [name='name']").toHaveText("second record");

    await contains(".o_data_row .o_data_cell").click();
    expect("#dialog_0 [name='name'] input").toHaveValue("second record");

    await contains("#dialog_0 .o_data_row .o_data_cell").click();
    expect("#dialog_1 [name='name'] input").toHaveValue("aaa");

    await contains("#dialog_1 [name='name'] input").edit("leonardo");
    await contains("#dialog_1 .o_form_button_save").click();
    expect("#dialog_1").toHaveCount(0);
    expect("#dialog_0 .o_data_row [name='name']").toHaveText("leonardo");

    await contains("#dialog_0 .o_data_row .o_data_cell").click();
    expect("#dialog_2 [name='name'] input").toHaveValue("leonardo");
    await contains("#dialog_2 .o_form_button_cancel").click();
    await contains("#dialog_0 .o_form_button_cancel").click();
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_data_row [name='name']").toHaveText("aaa");
});

test("discard a form dialog view and then reopen it with a domain based on a text field", async () => {
    Turtle._records[1].turtle_foo = "yop";
    Turtle._views = {
        form: `
            <form>
                <field name="name" invisible="turtle_foo == 'yop'"/>
                <field name="turtle_foo"/>
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="name"/>
                <field name="turtles">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row [name='name']").toHaveText("donatello");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name']").toHaveCount(0);
    expect(".modal [name='turtle_foo'] input").toHaveValue("yop");

    await contains(".modal [name='turtle_foo'] input").edit("display");
    expect(".modal [name='name'] input").toHaveValue("donatello");
    expect(".modal [name='turtle_foo'] input").toHaveValue("display");

    await contains(".modal .o_form_button_save").click();
    await contains(".o_form_button_cancel").click();
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name']").toHaveCount(0);
    expect(".modal [name='turtle_foo'] input").toHaveValue("yop");
});

test("onchange on one2many with x2many in list (many2many_tags) and form view (list)", async () => {
    expect.assertions(7);
    Turtle._fields.turtle_foo = fields.Char({ default: "a default value" });
    Partner._onChanges = {
        foo: function (obj) {
            obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
        },
    };
    onRpc("partner", "onchange", ({ args }) => {
        expect(args[3]).toEqual({
            display_name: {},
            foo: {},
            p: {
                fields: {
                    turtles: {
                        fields: {
                            display_name: {},
                            turtle_foo: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="p">
                    <list>
                        <field name="turtles" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="turtles">
                            <list editable="top">
                                <field name="turtle_foo"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1, {
        message: "the onchange should have created one record in the relation",
    });

    // open the created o2m record in a form view
    await contains(".o_data_row .o_data_cell").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_data_row").toHaveText("hello");

    // add a one2many subrecord and check if the default value is correctly applied
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal .o_data_row").toHaveCount(2);
    expect(".modal .o_data_row .o_field_widget[name=turtle_foo] input").toHaveValue(
        "a default value"
    );
});

test("embedded one2many with handle widget with minimum setValue calls", async () => {
    Turtle._records[0].turtle_int = 6;
    Turtle._records.push(
        {
            id: 4,
            turtle_int: 20,
            turtle_foo: "a1",
        },
        {
            id: 5,
            turtle_int: 9,
            turtle_foo: "a2",
        },
        {
            id: 6,
            turtle_int: 2,
            turtle_foo: "a3",
        },
        {
            id: 7,
            turtle_int: 11,
            turtle_foo: "a4",
        }
    );
    Partner._records[0].turtles = [1, 2, 3, 4, 5, 6, 7];

    patchWithCleanup(Record.prototype, {
        _update() {
            if (this.resModel === "turtle") {
                expect.step(`${this.resId}`);
            }
            return super._update(...arguments);
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row [name='turtle_foo']")).toEqual([
        "a3",
        "yop",
        "blip",
        "a2",
        "a4",
        "a1",
        "kawa",
    ]);

    const positions = [
        [6, 0, ["3", "6", "1", "2", "5", "7", "4"]], // move the last to the first line
        [5, 1, ["7", "6", "1", "2", "5"]], // move the penultimate to the second line
        [2, 5, ["1", "2", "5", "6"]], // move the third to the penultimate line
    ];
    for (const [sourceIndex, targetIndex, steps] of positions) {
        await contains(`tbody tr:eq(${sourceIndex}) .o_handle_cell`).dragAndDrop(
            `tbody tr:eq(${targetIndex})`
        );
        expect.verifySteps(steps);
    }

    expect(queryAllTexts(".o_data_row [name='turtle_foo']")).toEqual([
        "kawa",
        "a4",
        "yop",
        "blip",
        "a2",
        "a3",
        "a1",
    ]);
});

test("embedded one2many (editable list) with handle widget", async () => {
    Partner._records[0].p = [1, 2, 4];
    onRpc("web_save", (args) => {
        expect.step(args.method);
        expect(args.args[1].p).toEqual([
            [1, 2, { int_field: 0 }],
            [1, 4, { int_field: 1 }],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="int_field" widget="handle"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([
        "My little Foo Value",
        "blip",
        "yop",
    ]);

    expect.verifySteps([]);

    // Drag and drop the second line in first position
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop(".o_field_one2many tbody tr:eq(0)");

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([
        "blip",
        "My little Foo Value",
        "yop",
    ]);

    await contains(".o_data_cell.o_list_char").click();

    expect(".o_field_widget[name=foo] input").toHaveValue("blip");

    expect.verifySteps([]);

    await clickSave();

    expect.verifySteps(["web_save"]);
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([
        "blip",
        "My little Foo Value",
        "yop",
    ]);
});

test("one2many list order with handle widget", async () => {
    onRpc("web_read", (args) => {
        expect.step(`web_read`);
        expect(args.kwargs.specification.p.order).toBe("int_field ASC, id ASC");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="int_field" widget="handle"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect.verifySteps(["web_read"]);
});

test("one2many kanban order with handle widget", async () => {
    onRpc("web_read", (args) => {
        expect.step(`web_read`);
        expect(args.kwargs.specification.p.order).toBe("int_field ASC, id ASC");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <field name="int_field" widget="handle"/>
                        <templates>
                            <t t-name="card">
                                <field name="foo"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });
    expect.verifySteps(["web_read"]);
});

test("one2many field when using the pager", async () => {
    const ids = [];
    for (let i = 0; i < 45; i++) {
        const id = 10 + i;
        ids.push(id);
        Partner._records.push({
            id,
            name: `relational record ${id}`,
        });
    }
    Partner._records[0].p = ids.slice(0, 42);
    Partner._records[1].p = ids.slice(42);

    onRpc("web_read", (args) => {
        expect.step(`unity read ${args.args[0]}`);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
        resIds: [1, 2],
    });

    expect.verifySteps(["unity read 1"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    // move to record 2, which has 3 related records (and shouldn't contain the
    // related records of record 1 anymore)
    await contains(".o_form_view .o_control_panel .o_pager_next").click();
    expect.verifySteps(["unity read 2"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);

    // move back to record 1, which should contain again its first 40 related
    // records
    await contains(".o_form_view .o_control_panel .o_pager_previous").click();
    expect.verifySteps(["unity read 1"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    // move to the second page of the o2m: 1 RPC should have been done to fetch
    // the 2 subrecords of page 2, and those records should now be displayed
    await contains(".o_x2m_control_panel .o_pager_next").click();
    expect.verifySteps(["unity read 50,51"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);

    // move to record 2 again and check that everything is correctly updated
    await contains(".o_form_view .o_control_panel .o_pager_next").click();
    expect.verifySteps(["unity read 2"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);

    // move back to record 1 and move to page 2 again: all data should have
    // been correctly reloaded
    await contains(".o_form_view .o_control_panel .o_pager_previous").click();
    expect.verifySteps(["unity read 1"]);
    await contains(".o_x2m_control_panel .o_pager_next").click();
    expect.verifySteps(["unity read 50,51"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
});

test("edition of one2many field with pager", async () => {
    const ids = [];
    for (let i = 0; i < 45; i++) {
        const id = 10 + i;
        ids.push(id);
        Partner._records.push({
            id: id,
            name: "relational record " + id,
        });
    }
    Partner._records[0].p = ids;
    Partner._views = { form: '<form><field name="name"/></form>' };

    let saveCount = 0;
    let checkRead = false;
    let readIDs;
    onRpc("web_read", (args) => {
        if (checkRead) {
            readIDs = args.args[0];
            checkRead = false;
        }
    });
    onRpc("web_save", (args) => {
        expect.step("web_save");
        saveCount++;
        const commands = args.args[1].p;
        switch (saveCount) {
            case 1:
                expect(commands).toEqual([[0, commands[0][1], { name: "new record" }]]);
                break;
            case 2:
                expect(commands).toEqual([[2, 10]]);
                break;
            case 3:
                expect(commands).toEqual([
                    [0, commands[0][1], { name: "new record page 1" }],
                    [2, 11],
                    [2, 52],
                    [0, commands[3][1], { name: "new record page 2" }],
                ]);
                break;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    // add a record on page one
    checkRead = true;
    await contains(".o-kanban-button-new").click();
    await contains(".modal input").edit("new record");

    await contains(".modal .modal-footer .btn-primary").click();

    // checks
    expect(readIDs).toBe(undefined, { message: "should not have read any record" });
    expect(".o_kanban_record:not(.o_kanban_ghost):contains('new record')").toHaveCount(0);

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    // save
    await clickSave();

    // delete a record on page one
    checkRead = true;
    expect(".o_kanban_record:not(.o_kanban_ghost):eq(0)").toHaveText("relational record 10");

    await contains(".delete_icon").click(); // should remove record!!!

    // checks
    expect(readIDs).toEqual([50], {
        message: "should have read a record (to display 40 records on page 1)",
    });
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);
    // save
    await clickSave();

    // add and delete records in both pages
    checkRead = true;
    readIDs = undefined;
    // add and delete a record in page 1
    await contains(".o-kanban-button-new").click();
    await contains(".modal input").edit("new record page 1");
    await contains(".modal .modal-footer .btn-primary").click();
    expect(".o_kanban_record:not(.o_kanban_ghost):eq(0)").toHaveText("relational record 11", {
        message: "first record should be the one with id 11 (next checks rely on that)",
    });

    await contains(".delete_icon").click(); // should remove record!!!
    expect(readIDs).toEqual([51], {
        message: "should have read a record (to display 40 records on page 1)",
    });
    // add and delete a record in page 2
    await contains(".o_x2m_control_panel .o_pager_next").click();

    expect(".o_kanban_record:not(.o_kanban_ghost):eq(0)").toHaveText("relational record 52", {
        message: "first record should be the one with id 52 (next checks rely on that)",
    });

    checkRead = true;
    readIDs = undefined;
    await contains(".delete_icon").click(); // should remove record!!!
    await contains(".o-kanban-button-new").click();

    await contains(".modal input").edit("new record page 2");
    await contains(".modal .modal-footer .btn-primary").click();

    expect(readIDs).toBe(undefined, { message: "should not have read any record" });
    // checks
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);
    expect(".o_kanban_record:not(.o_kanban_ghost):contains('new record page 1')").toHaveCount(1);
    expect(".o_kanban_record:not(.o_kanban_ghost):contains('new record page 2')").toHaveCount(1);
    // save
    await clickSave();

    expect.verifySteps(["web_save", "web_save", "web_save"]);
});

test.tags("desktop");
test("edition of one2many field with pager on desktop", async () => {
    const ids = [];
    for (let i = 0; i < 45; i++) {
        const id = 10 + i;
        ids.push(id);
        Partner._records.push({
            id: id,
            name: "relational record " + id,
        });
    }
    Partner._records[0].p = ids;
    Partner._views = { form: '<form><field name="name"/></form>' };

    let saveCount = 0;
    let checkRead = false;
    onRpc("web_read", (args) => {
        if (checkRead) {
            checkRead = false;
        }
    });
    onRpc("web_save", (args) => {
        expect.step("web_save");
        saveCount++;
        const commands = args.args[1].p;
        switch (saveCount) {
            case 1:
                expect(commands).toEqual([[0, commands[0][1], { name: "new record" }]]);
                break;
            case 2:
                expect(commands).toEqual([[2, 10]]);
                break;
            case 3:
                expect(commands).toEqual([
                    [0, commands[0][1], { name: "new record page 1" }],
                    [2, 11],
                    [2, 52],
                    [0, commands[3][1], { name: "new record page 2" }],
                ]);
                break;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 45");

    // add a record on page one
    checkRead = true;
    await contains(".o-kanban-button-new").click();
    await contains(".modal input").edit("new record");

    await contains(".modal .modal-footer .btn-primary").click();

    // checks
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 46");

    // save
    await clickSave();

    // delete a record on page one
    checkRead = true;

    await contains(".delete_icon").click(); // should remove record!!!

    // checks
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 45");
    // save
    await clickSave();

    // add and delete records in both pages
    checkRead = true;
    // add and delete a record in page 1
    await contains(".o-kanban-button-new").click();
    await contains(".modal input").edit("new record page 1");
    await contains(".modal .modal-footer .btn-primary").click();

    await contains(".delete_icon").click(); // should remove record!!!
    // add and delete a record in page 2
    await contains(".o_x2m_control_panel .o_pager_next").click();

    checkRead = true;
    await contains(".delete_icon").click(); // should remove record!!!
    await contains(".o-kanban-button-new").click();

    await contains(".modal input").edit("new record page 2");
    await contains(".modal .modal-footer .btn-primary").click();

    // checks
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("41-45 / 45");
    // save
    await clickSave();

    expect.verifySteps(["web_save", "web_save", "web_save"]);
});

test("When viewing one2many records in an embedded kanban, the delete button should say 'Delete' and not 'Remove'", async () => {
    expect.assertions(1);
    Turtle._views = {
        form: `
            <form>
                <h3>Data</h3>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <h3>Record 1</h3>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    // Opening the record to see the footer buttons
    await contains(".o_kanban_record").click();

    expect(".o_btn_remove").toHaveText("Delete");
});

test("open a record in a one2many kanban (mode 'readonly')", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form edit="0">
                <field name="turtles">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:eq(0)").toHaveText("donatello");

    await contains(".o_kanban_record").click();

    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] span").toHaveText("donatello");
});

test("open a record in a one2many kanban (mode 'edit')", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:eq(0)").toHaveText("donatello");

    await contains(".o_kanban_record").click();

    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] input").toHaveValue("donatello");
});

test("open a record in an one2many readonly", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" readonly='1'>
                    <list>
                        <field name="name" />
                    </list>
                    <form>
                        <field name="name" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] span").toHaveText("donatello");

    await contains(".modal .o_form_button_cancel").click();
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] span").toHaveText("donatello");
});

test("open a record in a one2many kanban with an x2m in the form", async () => {
    Partner._records[0].p = [2];
    Partner._records[1].p = [4];

    Partner._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    };

    const def = new Deferred();
    onRpc("web_read", async (args) => {
        if (args.args[0][0] === 2) {
            expect.step("web_read: 2");
            await def;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_kanban_record").click();
    def.resolve();
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal [name=name] input").toHaveValue("second record");
    expect(queryAllTexts(".modal .o_data_row")).toEqual(["aaa"]);

    expect.verifySteps(["web_read: 2"]);
});

test("one2many in kanban: add a line custom control create editable", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <kanban>
                        <control>
                            <create string="Add food" context="" />
                            <create string="Add pizza" context="{'default_name': 'pizza'}"/>
                        </control>
                        <control>
                            <create string="Add pasta" context="{'default_name': 'pasta'}"/>
                        </control>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    const createButtons = queryAll(".o_x2m_control_panel .o_cp_buttons button");
    expect(queryAllTexts(createButtons)).toEqual(["Add food", "Add pizza", "Add pasta"]);

    await contains(createButtons[0]).click();
    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] input").toHaveValue("");

    await contains(".modal .o_form_button_cancel").click();
    await contains(createButtons[1]).click();
    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] input").toHaveValue("pizza");

    await contains(".modal .o_form_button_cancel").click();
    await contains(createButtons[2]).click();
    expect(".modal").toHaveCount(1);
    expect(".modal div[name=name] input").toHaveValue("pasta");
});

test("one2many in kanban: add a line custom control create editable (2)", async () => {
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    onRpc("do_something", (args) => {
        expect.step("do_something");
        expect(args.kwargs.context.parent_id).toBe(2);
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <kanban>
                        <control>
                            <create string="Create" context="{}" />
                            <button string="Action Button" name="do_something" type="object" context="{'parent_id': parent.id}"/>
                        </control>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 2,
    });

    expect(queryAllTexts(".o_x2m_control_panel .o_cp_buttons button")).toEqual([
        "Create",
        "Action Button",
    ]);

    await contains(".o_x2m_control_panel .o_cp_buttons button:eq(1)").click();
    expect.verifySteps(["do_something"]);
});

test("add record in a one2many non editable list with context", async () => {
    expect.assertions(1);

    onRpc("turtle", "onchange", ({ kwargs }) => {
        // done by the X2ManyFieldDialog
        expect(kwargs.context).toEqual({
            abc: 2,
            allowed_company_ids: [1],
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles" context="{'abc': int_field}">
                    <list><field name="name"/></list>
                    <form><field name="name"/></form>
                </field>
            </form>`,
    });

    await contains(".o_field_widget[name=int_field] input").edit("2");
    await contains(".o_field_x2many_list_row_add a").click();
});

test.tags("desktop");
test("edition of one2many field, with onchange and not inline sub view", async () => {
    Turtle._onChanges.turtle_int = function (obj) {
        obj.turtle_foo = String(obj.turtle_int);
    };
    Partner._onChanges.turtles = function () {};
    Turtle._views = {
        list: `
                <list>
                    <field name="turtle_foo"/>
                </list>`,
        form: `
                <form>
                    <group>
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                    </group>
                </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="turtles" widget="one2many"/>
                </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="turtle_int"] input').edit("5");
    await contains(".modal-footer button.btn-primary").click();
    let firstCellOfSecondRow = ".o_data_cell.o_list_char:eq(1)";
    expect(firstCellOfSecondRow).toHaveText("5");
    await contains(firstCellOfSecondRow).click();

    await contains('div[name="turtle_int"] input').edit("3");
    await contains(".modal-footer button.btn-primary").click();
    firstCellOfSecondRow = ".o_data_cell.o_list_char:eq(1)";
    expect(firstCellOfSecondRow).toHaveText("3");
});

test.tags("desktop");
test("onchange specification complete after open sub form view not inline", async () => {
    Partner._onChanges.name = () => {};
    Turtle._views = {
        form: `
                <form>
                    <field name="name"/>
                    <field name="partner_ids">
                        <list>
                            <field name="name"/>
                        </list>
                    </field>
                </form>`,
    };
    onRpc("partner", "onchange", ({ args }) => {
        if (args[1].name === "test") {
            expect(args[3]).toEqual({
                name: {},
                display_name: {},
                turtles: {
                    fields: {
                        turtle_foo: {},
                    },
                    limit: 40,
                    order: "",
                },
            });
        } else if (args[1].name === "test2") {
            expect(args[3]).toEqual({
                name: {},
                display_name: {},
                turtles: {
                    fields: {
                        name: {},
                        partner_ids: {
                            fields: {
                                name: {},
                            },
                            limit: 40,
                            order: "",
                        },
                        turtle_foo: {},
                    },
                    limit: 40,
                    order: "",
                },
            });
            return {
                value: {
                    turtles: [
                        [
                            1,
                            2,
                            {
                                name: "yop",
                                partner_ids: [[1, 2, { name: "plop" }]],
                            },
                        ],
                    ],
                },
            };
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="name"/>
                    <field name="turtles">
                        <list>
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });
    await contains("div[name='name'] input").edit("test");
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name'] input").toHaveValue("donatello");
    expect(queryAllTexts(".modal .o_data_row")).toEqual(["second record", "aaa"]);

    await contains(".modal .o_form_button_save").click();
    await contains("div[name='name'] input").edit("test2");
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal [name='name'] input").toHaveValue("yop");
    expect(queryAllTexts(".modal .o_data_row")).toEqual(["plop", "aaa"]);
});

test("sorting one2many fields", async () => {
    Partner._fields.foo.sortable = true;
    Partner._records.push({ id: 23, foo: "abc", int_field: 1 });
    Partner._records.push({ id: 24, foo: "xyz", int_field: 1 });
    Partner._records.push({ id: 25, foo: "def", int_field: 2 });
    Partner._records[0].p = [23, 24, 25];

    let rpcCount = 0;
    onRpc(() => {
        rpcCount++;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="foo"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    rpcCount = 0;
    expect(queryAllTexts(".o_data_cell[name='foo']")).toEqual(["abc", "xyz", "def"]);

    await contains("table thead [data-name='foo'].o_column_sortable").click();
    expect(rpcCount).toBe(0, { message: "in memory sort, no RPC should have been done" });
    expect(queryAllTexts(".o_data_cell[name='foo']")).toEqual(["abc", "def", "xyz"]);

    await contains("table thead [data-name='foo'].o_column_sortable").click();
    expect(queryAllTexts(".o_data_cell[name='foo']")).toEqual(["xyz", "def", "abc"]);

    await contains("table thead [data-name='int_field'].o_column_sortable").click();
    expect(queryAllTexts(".o_data_cell[name='foo']")).toEqual(["xyz", "abc", "def"]);

    await contains("table thead [data-name='int_field'].o_column_sortable").click();
    expect(queryAllTexts(".o_data_cell[name='foo']")).toEqual(["def", "xyz", "abc"]);
});

test("sorting one2many fields with multi page", async () => {
    Partner._records.push({ id: 23, foo: "abc", int_field: 1 });
    Partner._records.push({ id: 24, foo: "xyz", int_field: 1 });
    Partner._records.push({ id: 25, foo: "def", int_field: 2 });
    Partner._records.push({ id: 26, foo: "otc", int_field: 2 });
    Partner._records[0].p = [23, 24, 25, 26];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list limit="2">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row")).toEqual(["abc 1", "xyz 1"]);

    await contains("table thead [data-name='int_field'].o_column_sortable").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["abc 1", "xyz 1"]);

    await contains("table thead [data-name='foo'].o_column_sortable").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["abc 1", "def 2"]);

    await contains(".o_field_widget[name='p'] .o_pager_next").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["otc 2", "xyz 1"]);
});

test("one2many list field edition", async () => {
    Partner._records.push({
        id: 3,
        name: "relational record 1",
    });
    Partner._records[1].p = [3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    expect(".o_field_one2many tbody td:eq(0)").toHaveText("relational record 1");

    await contains(".o_field_one2many tbody td").click();
    expect(".o_field_one2many tbody .o_data_row:eq(0)").toHaveClass("o_selected_row");
    await contains(".o_field_one2many tbody td input").edit("new value", { confirm: false });
    expect(".o_field_one2many tbody .o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_field_one2many tbody td input").toHaveValue("new value");

    // leave o2m edition
    await contains(".o_form_view").click();
    expect(".o_field_one2many tbody .o_data_row:eq(0)").not.toHaveClass("o_selected_row");

    // discard changes
    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);
    expect(".o_field_one2many tbody td:eq(0)").toHaveText("relational record 1");

    // edit again and save
    await contains(".o_field_one2many tbody td").click();
    await contains(".o_field_one2many tbody td input").edit("new value");
    await contains(".o_form_view").click();
    await clickSave();

    expect(".o_field_one2many tbody td:eq(0)").toHaveText("new value");
});

test("one2many list: create action disabled", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list create="0">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_field_x2many_list_row_add").toHaveCount(0);
});

test("one2many list: cannot open record in editable list and form in readonly mode", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form edit="0">
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_cell[name='name']").toHaveCount(1);
    await contains(".o_data_cell[name='name']").click();
    expect(".modal-dialog").toHaveCount(0);
});

test("one2many list: cannot open record in editable=bottom and edit=false list", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom" edit="false">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_cell[name='name']").toHaveCount(1);
    await contains(".o_data_cell[name='name']").click();
    expect(".modal-dialog").toHaveCount(0);
});

test("one2many list: conditional create/delete actions", async () => {
    Partner._records[0].p = [2, 4];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // bar is true -> create and delete action are available
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect("td.o_list_record_remove button").toHaveCount(2);

    // set bar to false -> create and delete action are no longer available
    await contains('.o_field_widget[name="bar"] input').click();

    expect(".o_field_x2many_list_row_add").toHaveCount(0);
    expect("td.o_list_record_remove button").toHaveCount(0);
});

test("boolean field in a one2many must be directly editable", async () => {
    Partner._records[0].p = [2, 4];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="bar"/>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_cell[name='bar'] input:eq(0)").toBeChecked();
    expect(".o_data_cell[name='bar'] input:eq(1)").not.toBeChecked();

    await contains('[name="bar"] .o-checkbox').click();
    expect(".o_data_cell[name='bar'] input:eq(0)").not.toBeChecked();
    expect(".o_data_cell[name='bar'] input:eq(1)").not.toBeChecked();
});

test("many2many list: unlink two records", async () => {
    expect.assertions(4);
    Partner._records[0].p = [1, 2, 4];
    Partner._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].p).toEqual([[3, 1]], { message: "should send a command 3 (unlink)" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" widget="many2many">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect("td.o_list_record_remove button").toHaveCount(3);

    await contains("td.o_list_record_remove button").click();
    expect("td.o_list_record_remove button").toHaveCount(2);

    await contains("tr.o_data_row td").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(0);

    await contains(".modal .btn-secondary").click();
    await clickSave();
});

test("one2many list: deleting one records", async () => {
    expect.assertions(3);
    Partner._records[0].p = [1, 2, 4];
    Partner._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].p).toEqual([[2, 1]]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect("td.o_list_record_remove button").toHaveCount(3);

    await contains("td.o_list_record_remove button").click();
    expect("td.o_list_record_remove button").toHaveCount(2);

    // save and check that the correct command has been generated
    await clickSave();

    // FIXME: it would be nice to test that the view is re-rendered correctly,
    // but as the relational data isn't re-fetched, the rendering is ok even
    // if the changes haven't been saved
});

test("one2many kanban: edition", async () => {
    expect.assertions(17);

    Partner._records[0].p = [2];
    onRpc("web_save", (args) => {
        const commands = args.args[1].p;
        expect(commands).toEqual([
            [
                0,
                commands[0][1],
                {
                    color: "red",
                    name: "new subrecord 3",
                    foo: "My little Foo Value",
                },
            ],
            [2, 2],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        // color will be in the kanban but not in the form
        // foo will be in the form but not in the kanban
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                    <field name="name"/>
                                    <field name="color"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="name"/>
                        <field name="foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span:eq(0)").toHaveText("second record");
    expect(".o_kanban_record span:eq(1)").toHaveText("Red");
    expect(".delete_icon").toHaveCount(1);
    expect(".o_field_one2many .o-kanban-button-new").toHaveCount(1);
    expect(".o_field_one2many .o-kanban-button-new").toHaveClass("btn-secondary");
    expect(".o_field_one2many .o-kanban-button-new").toHaveText("Add");

    // edit existing subrecord
    await contains(".o_kanban_record:eq(0)").click();

    await contains(".modal .o_form_view .o_field_widget:eq(0) input").edit("new name");
    await contains(".modal .modal-footer .btn-primary:eq(0)").click();
    expect(".o_kanban_record span:first").toHaveText("new name");

    // create a new subrecord
    await contains(".o-kanban-button-new:eq(0)").click();
    await contains(".modal .o_form_view .o_field_widget:eq(0) input").edit("new subrecord 1");
    await contains(".modal .modal-footer .btn-primary:eq(0)").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_kanban_record:eq(1) span:eq(0)").toHaveText("new subrecord 1", {
        message: 'value of newly created subrecord should be "new subrecord 1"',
    });
    // create two new subrecords
    await contains(".o-kanban-button-new:eq(0)").click();
    await contains(".modal .o_form_view .o_field_widget:eq(0) input").edit("new subrecord 2");
    await contains(".modal .modal-footer .btn-primary:eq(1)").click();
    await contains(".modal .o_form_view .o_field_widget:eq(0) input").edit("new subrecord 3");
    await contains(".modal .modal-footer .btn-primary:eq(0)").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    // delete subrecords
    await contains(".o_kanban_record:eq(0)").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(1);
    await contains(".modal .modal-footer .o_btn_remove:eq(0)").click();
    expect(".o_modal").toHaveCount(0, { message: "modal should have been closed" });
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);
    await contains(".o_kanban_renderer .delete_icon:first():eq(0)").click();
    await contains(".o_kanban_renderer .delete_icon:first():eq(0)").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span:first").toHaveText("new subrecord 3", {
        message: 'the remaining subrecord should be "new subrecord 3"',
    });

    // save and check that the correct command has been generated
    await clickSave();
});

test("one2many kanban (editable): properly handle add-label node attribute", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" add-label="Add turtle" mode="kanban">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts('.o_field_one2many[name="turtles"] .o-kanban-button-new')).toEqual(
        ["Add turtle"],
        { message: "In O2M Kanban, Add button should have 'Add turtle' label" }
    );
});

test("one2many kanban: create action disabled", async () => {
    Partner._records[0].p = [4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban create="0">
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o-kanban-button-new").toHaveCount(0);
    expect(".o_field_x2many_kanban .delete_icon").toHaveCount(1);
});

test("one2many kanban: conditional create/delete actions", async () => {
    Partner._records[0].p = [2, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="name"/>
                        <field name="foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    // bar is initially true -> create and delete actions are available
    expect(".o-kanban-button-new").toHaveCount(1, { message: '"Add" button should be available' });

    await contains(".o_kanban_record:first").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(1, {
        message: "There should be a Remove Button inside modal",
    });

    await contains(".modal .o_form_button_cancel").click();
    // set bar false -> create and delete actions are no longer available
    await contains('.o_field_widget[name="bar"] input').click();
    expect(".o-kanban-button-new").toHaveCount(0, {
        message: '"Add" button should not be available as bar is False',
    });

    await contains(".o_kanban_record:first").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(0, {
        message: "There should not be a Remove Button as bar field is False",
    });
});

test.tags("desktop");
test("editable one2many list, pager is updated on desktop", async () => {
    Turtle._records.push({ id: 4, turtle_foo: "stephen hawking" });
    Partner._records[0].turtles = [1, 2, 3, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record, add value to turtle_foo then click in form view to confirm it
    await contains(".o_field_x2many_list_row_add a").click();

    await contains('div[name="turtle_foo"] input').edit("nora");

    await contains(getFixture()).click();

    expect(".o_field_widget[name=turtles] .o_pager").toHaveText("1-4 / 5");
});

test("one2many list (non editable): edition", async () => {
    expect.assertions(11);

    let nbWrite = 0;
    Partner._records[0].p = [2, 4];
    onRpc("web_save", (args) => {
        nbWrite++;
        expect(args.args[1]).toEqual({
            p: [
                [1, 2, { name: "new name" }],
                [2, 4],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                        <field name="qux"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect("td.o_list_number").toHaveCount(2);
    expect(".o_list_renderer tbody td:eq(0)").toHaveText("second record");
    expect(".o_list_record_remove").toHaveCount(2);
    expect(".o_field_x2many_list_row_add").toHaveCount(1);

    // edit first record
    await contains(".o_list_renderer .o_data_cell").click();
    expect(".o_list_renderer .o_data_cell:eq(0)").toHaveClass("o_readonly_modifier");

    await contains(".modal .o_form_editable input").edit("new name");

    contains(".modal .modal-footer .btn-primary").click();
    await animationFrame();
    expect(".o_list_renderer tbody td:eq(0)").toHaveText("new name");
    expect(nbWrite).toBe(0, { message: "should not have write anything in DB" });

    // remove second record
    contains(".o_list_record_remove:eq(1)").click();
    await animationFrame();
    expect("td.o_list_number").toHaveCount(1);
    expect(".o_list_renderer tbody td:eq(0)").toHaveText("new name");

    await clickSave(); // save the record
    expect(nbWrite).toBe(1, { message: "should have write the changes in DB" });
});

test("one2many list (editable): edition, part 2", async () => {
    expect.assertions(11);
    onRpc("web_save", (args) => {
        // Would be nice to assert this way, but we don't control the virtual ids index
        // expect(args.args[1].p).toEqual([
        //     [0, "virtual_2", { foo: "gemuse" }],
        //     [0, "virtual_1", { foo: "kartoffel" }],
        // ]);
        expect(args.args[1].p[0][0]).toBe(0);
        expect(args.args[1].p[1][0]).toBe(0);
        expect(args.args[1].p[0][2]).toEqual({ foo: "gemuse" });
        expect(args.args[1].p[1][2]).toEqual({ foo: "kartoffel" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    // edit mode, then click on Add an item and enter a value
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_selected_row > td input").edit("kartoffel", { confirm: "false" });
    expect("td .o_field_char input").toHaveValue("kartoffel");

    // click again on Add an item
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_data_cell:eq(1)").toHaveText("kartoffel");
    expect(".o_selected_row > td input").toHaveCount(1);
    expect("tr.o_data_row").toHaveCount(2);

    // enter another value and save
    await contains(".o_selected_row > td input").edit("gemuse", { confirm: "false" });
    await clickSave();
    expect("tr.o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_cell")).toEqual(["gemuse", "kartoffel"]);
});

test("one2many list (editable): edition, part 3", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
    expect("tr.o_data_row").toHaveCount(1);
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="turtle_foo"] input').edit("nora", { confirm: "false" });
    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(3);

    // cancel the edition
    await contains(".o_form_button_cancel").click();

    expect(".modal").toHaveCount(0);
    expect("tr.o_data_row").toHaveCount(1);
});

test.tags("desktop");
test("one2many list (editable): edition, part 4", async () => {
    let i = 0;
    Turtle._onChanges = {
        turtle_trululu: function (obj) {
            if (i) {
                obj.turtle_description = "Some Description";
            }
            i++;
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_trululu"/>
                            <field name="turtle_description"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 2,
    });

    // edit mode, then click on Add an item
    expect("tr.o_data_row").toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row textarea").toHaveValue("");

    // add a value in the turtle_trululu field to trigger an onchange
    await clickFieldDropdown("turtle_trululu");
    await press("Enter");
    await animationFrame();
    expect(".o_data_row textarea").toHaveValue("Some Description");
});

test("one2many list (editable): edition, part 5", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
    expect("tr.o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("blip");
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=turtle_foo] input").edit("aaa", { confirm: "false" });
    expect("tr.o_data_row").toHaveCount(2);
    await contains(".o_list_record_remove:eq(1)").click();
    expect("tr.o_data_row").toHaveCount(1);

    // cancel the edition
    await contains(".o_form_button_cancel").click();
    expect("tr.o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("blip");
});

test("one2many list (editable): discarding required empty data", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    // edit mode, then click on Add an item, then click elsewhere
    expect("tr.o_data_row").toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(getFixture()).click();
    expect("tr.o_data_row").toHaveCount(0);

    // click on Add an item again, then click on save
    await contains(".o_field_x2many_list_row_add a").click();
    await clickSave();
    expect("tr.o_data_row").toHaveCount(0);

    expect.verifySteps(["get_views", "web_read", "onchange", "onchange"]);
});

test.tags("desktop");
test("discard O2M field with close button", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name" />
                    </list>
                    <form>
                        <field name="name" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveText("second record");

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".modal .o_field_widget[name=name] input").toHaveValue("second record");

    await contains(".modal .o_field_widget[name=name] input").edit("plop");
    await contains(".modal .btn-close").click();
    expect(".o_data_row").toHaveText("second record");

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".modal .o_field_widget[name=name] input").toHaveValue("second record");
});

test("editable one2many list, adding line when only one page", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record, to reach the page size limit
    await contains(".o_field_x2many_list_row_add a").click();
    // the record currently being added should not count in the pager
    expect(".o_field_widget[name=turtles] .o_pager").toHaveCount(0);

    // enter value in turtle_foo field and click outside to unselect the row
    await contains('.o_field_widget[name="turtle_foo"] input').edit("nora");
    await contains(getFixture()).click();
    expect(".o_selected_row").toHaveCount(0);
    expect(".o_field_widget[name=turtles] .o_pager").toHaveCount(0);

    await clickSave();
    expect(".o_field_widget[name=turtles] .o_pager").toHaveCount(1);
});

test.tags("desktop");
test("editable one2many list, adding line when only one page on desktop", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record, to reach the page size limit
    await contains(".o_field_x2many_list_row_add a").click();

    // enter value in turtle_foo field and click outside to unselect the row
    await contains('.o_field_widget[name="turtle_foo"] input').edit("nora");
    await contains(getFixture()).click();
    await clickSave();
    expect(".o_field_widget[name=turtles] .o_pager").toHaveText("1-3 / 4");
});

test("editable one2many list, adding line, then discarding", async () => {
    Turtle._records.push({ id: 4, turtle_foo: "stephen hawking" });
    Partner._records[0].turtles = [1, 2, 3, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record, then discard
    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);

    expect(".o_field_widget[name=turtles] .o_pager").toBeVisible();
});

test.tags("desktop");
test("editable one2many list, adding line, then discarding on desktop", async () => {
    Turtle._records.push({ id: 4, turtle_foo: "stephen hawking" });
    Partner._records[0].turtles = [1, 2, 3, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record, then discard
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=turtles] .o_pager").toHaveText("1-3 / 4");
});

test("editable one2many list, required field and pager", async () => {
    Turtle._records.push({ id: 4, turtle_foo: "stephen hawking" });
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    Partner._records[0].turtles = [1, 2, 3, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a (empty) record
    await contains(".o_field_x2many_list_row_add a").click();

    // go on next page. The new record is not valid and should be discarded
    await contains(".o_field_widget[name=turtles] .o_pager_next").click();
    expect("tr.o_data_row").toHaveCount(1);
});

test.tags("desktop");
test("editable one2many list, required field, pager and confirm discard on desktop", async () => {
    Turtle._records.push({ id: 4, turtle_foo: "stephen hawking" });
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    Partner._records[0].turtles = [1, 2, 3, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a record with a dirty state, but not valid
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_field_widget[name="turtle_int"] input').edit(4321);

    // try to go to next page. The new record is not valid, but dirty so we should
    // stay on the current page, and the record should be marked as invalid
    await contains(".o_field_widget[name=turtles] .o_pager_next").click();

    expect(".o_field_widget[name=turtles] .o_pager").toHaveText("1-4 / 5");

    expect(".o_field_widget[name=turtles] .o_pager").toHaveText("1-4 / 5");
    expect(".o_field_widget[name=turtle_foo].o_field_invalid").toHaveCount(1);
});

test("save a record with not new, dirty and invalid subrecord", async () => {
    Partner._records[0].p = [2];
    Partner._records[1].name = ""; // invalid record
    onRpc("write", () => {
        throw new Error("Should not call write as record is invalid");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name" required="1"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        mode: "edit",
    });

    expect(".o_form_editable").toHaveCount(1);
    await contains(".o_data_cell").click(); // edit the first row
    expect(".o_data_row").toHaveClass("o_selected_row");
    await contains(".o_field_widget[name=int_field] input").edit(44);
    await contains(".o_form_button_save").click();
    expect(".o_form_editable").toHaveCount(1);
    expect(".o_invalid_cell").toHaveCount(1);
});

test("editable one2many list, adding, discarding, and pager", async () => {
    Partner._records[0].turtles = [1];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add 4 records (to have more records than the limit)
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_field_widget[name="turtle_foo"] input').edit("nora", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_field_widget[name="turtle_foo"] input').edit("nora", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_field_widget[name="turtle_foo"] input').edit("nora", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();

    expect("tr.o_data_row").toHaveCount(5);
    expect(".o_field_widget[name=turtles] .o_pager").toHaveCount(0);

    // discard
    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);

    expect("tr.o_data_row").toHaveCount(1);
    expect(".o_field_widget[name=turtles] .o_pager").toHaveCount(0);
});

test("unselecting a line with missing required data", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    // edit mode, then click on Add an item, then click elsewhere
    expect("tr.o_data_row").toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(1);

    // adding a value in the non required field, so it is dirty, but with
    // a missing required field
    await contains('.o_field_widget[name="turtle_int"] input').edit("12345");

    // click elsewhere
    await contains(getFixture()).click();
    expect(".modal").toHaveCount(0);

    // the line should still be selected
    expect("tr.o_data_row.o_selected_row").toHaveCount(1);

    // click discard
    await contains(".o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);
    expect("tr.o_data_row").toHaveCount(0);
});

test("pressing enter in a o2m with a required empty field", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    // edit mode, then click on Add an item, then press enter
    await contains(".o_field_x2many_list_row_add a").click();
    await press("Enter");
    await animationFrame();
    expect('div[name="turtle_foo"]').toHaveClass("o_field_invalid");
    expect.verifySteps(["get_views", "web_read", "onchange"]);
});

test("pressing enter several times in a one2many", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");

    await contains("[name='turtle_foo'] input").edit("a", { confirm: false });
    await press("Enter");
    await animationFrame();
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:eq(1)").toHaveClass("o_selected_row");

    await contains("[name='turtle_foo'] input").edit("a", { confirm: false });
    await press("Enter");
    await animationFrame();
    expect(".o_data_row").toHaveCount(3);
    expect(".o_data_row:eq(2)").toHaveClass("o_selected_row");

    // this is a weird case, but there's no required fields, so the record is already valid, we can press Enter directly.
    await press("Enter");
    await animationFrame();
    expect(".o_data_row").toHaveCount(4);
    expect(".o_data_row:eq(3)").toHaveClass("o_selected_row");
});

test("creating a new line in an o2m with an handle field does not focus the handler", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect("[name='turtle_foo'] input").toBeFocused();

    await press("Enter");
    await animationFrame();
    expect("[name='turtle_foo'] input").toBeFocused();
});

test("editing a o2m, with required field and onchange", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    Turtle._onChanges = {
        turtle_foo: function (obj) {
            obj.turtle_int = obj.turtle_foo.length;
        },
    };
    onRpc((args) => {
        if (args.method) {
            expect.step(args.method);
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                            <field name="turtle_int"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 2,
    });

    // edit mode, then click on Add an item
    expect("tr.o_data_row").toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a").click();

    // input some text in required turtle_foo field
    await contains('.o_field_widget[name="turtle_foo"] input').edit("aubergine", {
        confirm: "blur",
    });
    expect('.o_field_cell[name="turtle_int"]').toHaveText("9");

    // save and check everything is fine
    await clickSave();

    expect(".o_data_row .o_data_cell.o_list_char").toHaveText("aubergine");
    expect(".o_data_row .o_data_cell.o_list_number").toHaveText("9");

    expect.verifySteps(["get_views", "web_read", "onchange", "onchange", "web_save"]);
});

test("editable o2m, pressing ESC discard current changes", async () => {
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect("tr.o_data_row").toHaveCount(0);
    expect.verifySteps(["get_views", "web_read", "onchange"]);
});

test("editable o2m with required field, pressing ESC discard current changes", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect("tr.o_data_row").toHaveCount(0);
    expect.verifySteps(["get_views", "web_read", "onchange"]);
});

test("pressing escape in editable o2m list in dialog", async () => {
    Partner._views = {
        form: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal .o_data_row.o_selected_row").toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(0);
});

test.tags("desktop");
test("editable o2m with onchange and required field: delete an invalid line", async () => {
    Partner._onChanges = {
        turtles: function () {},
    };
    Partner._records[0].turtles = [1];
    Turtle._records[0].product_id = 37;
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="turtles">
                        <list editable="top">
                            <field name="product_id"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    expect.verifySteps(["get_views", "web_read"]);
    await contains(".o_data_cell").click();
    await contains(".o_field_widget[name=product_id] input").clear();
    // no onchange should be done as line is invalid
    expect.verifySteps([]);
    await contains(".o_list_record_remove").click();
    // onchange should have been done
    expect.verifySteps(["onchange"]);
});

test("onchange in a one2many", async () => {
    Partner._records.push({
        id: 3,
        foo: "relational record 1",
    });
    Partner._records[1].p = [3];
    Partner._onChanges = { p: () => {} };
    onRpc("onchange", (args) => {
        return {
            value: {
                p: [
                    [2, 3], // delete 3
                    [0, 0, { foo: "from onchange" }], // create new
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_one2many tbody td").click();
    await contains(".o_field_one2many tbody td input").edit("new value", { confirm: false });
    await clickSave();

    expect(".o_field_one2many tbody td:eq(0)").toHaveText("from onchange");
});

test("one2many, default_get and onchange (basic)", async () => {
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [],
    });
    Partner._onChanges = { p: () => {} };
    onRpc("onchange", (args) => {
        return {
            value: {
                p: [
                    [0, 0, { foo: "from onchange" }], // create new
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
    });

    expect("td:eq(0)").toHaveText("from onchange");
});

test("one2many and default_get (with date)", async () => {
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [[0, false, { date: "2017-10-08", p: [] }]],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="date"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".o_data_cell").toHaveText("10/08/2017");
});

test("one2many and onchange (with integer)", async () => {
    Turtle._onChanges = {
        turtle_int: function () {},
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect("td:eq(0)").toHaveText("9");
    contains("td").click();
    await contains('td [name="turtle_int"] input').edit("3", { confirm: "blur" });
    expect.verifySteps(["get_views", "web_read", "onchange"]);
});

test("one2many and onchange (with date)", async () => {
    Partner._onChanges = {
        date: function () {},
    };
    Partner._records[0].p = [2];
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="date"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect("td:eq(0)").toHaveText("01/25/2017");

    contains("td:eq(0)").click();
    await contains("td:eq(0) .o_field_date input").click();
    contains(getPickerCell("1")).click();
    await clickSave();

    expect.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
});

test("one2many and onchange only write modified field", async () => {
    expect.assertions(2);

    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [
                [
                    1,
                    3,
                    {
                        name: "coucou",
                        turtle_foo: "has changed",
                        turtle_int: 42,
                    },
                ],
            ];
        },
    };

    Partner._records[0].turtles = [3];
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual(
            [
                [
                    1,
                    3,
                    {
                        name: "coucou",
                        turtle_foo: "has changed",
                        turtle_int: 42,
                    },
                ],
            ],
            { message: "correct commands should be sent (only send changed values)" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name"/>
                        <field name="product_id"/>
                        <field name="turtle_bar"/>
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                        <field name="turtle_qux"/>
                        <field name="turtle_ref"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(1);
    await contains(".o_field_one2many td").click();
    await contains(".o_field_widget[name=name] input").edit("blurp");

    await clickSave();
});

test("one2many with CREATE _onChanges correctly refreshed", async () => {
    let delta = 0;
    const fieldRegistry = registry.category("fields");
    for (const [name, field] of fieldRegistry.getEntries()) {
        class DeltaField extends field.component {
            setup() {
                super.setup();
                onWillStart(() => {
                    delta++;
                });
                onWillDestroy(() => {
                    delta--;
                });
            }
        }
        fieldRegistry.add(name, { ...field, component: DeltaField }, { force: true });
    }
    let _onChangestep = 0;

    Partner._records[0].turtles = [];
    Partner._onChanges = {
        turtles: function (obj) {
            // the onchange will either:
            //  - create a second line if there is only one line
            //  - edit the second line if there are two lines
            if (_onChangestep === 1) {
                obj.turtles = [
                    [
                        1,
                        obj.turtles[0][1],
                        {
                            name: "first",
                        },
                    ],
                    [
                        0,
                        0,
                        {
                            name: "second",
                            turtle_int: -obj.turtles[0][2].turtle_int,
                        },
                    ],
                ];
            } else if (_onChangestep === 2) {
                obj.turtles = [
                    [
                        1,
                        obj.turtles[1][1],
                        {
                            turtle_int: -obj.turtles[0][2].turtle_int,
                        },
                    ],
                ];
            }
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name" widget="char"/>
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a").click();
    // trigger the first onchange
    _onChangestep = 1;
    await contains('[name="turtle_int"] input').edit("10", { confirm: "blur" });
    // put the list back in non edit mode
    await click('[name="foo"] input');
    expect(queryAllTexts(".o_data_row")).toEqual(["first 10", "second -10"]);

    // trigger the second onchange
    _onChangestep = 2;
    await contains(".o_field_x2many_list tbody tr td").click();
    await contains('[name="turtle_int"] input').edit("20", { confirm: "blur" });
    await click('[name="foo"] input');
    expect(queryAllTexts(".o_data_row")).toEqual(["first 20", "second -20"]);
    expect(".o_field_widget").toHaveCount(delta);

    await clickSave();
    expect(queryAllTexts(".o_data_row")).toEqual(["first 20", "second -20"]);
});

test("editable one2many with sub widgets are rendered in readonly", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo" widget="char" readonly="turtle_int == 11111"/>
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_form_view .o_field_x2many_list_row_add ").toHaveCount(1);
    expect(".o_form_view input").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_form_view .o_field_x2many_list_row_add ").toHaveCount(1);
    expect(".o_form_view input").toHaveCount(2);
});

test("one2many editable list with onchange keeps the order", async () => {
    Partner._records[0].p = [1, 2, 4];
    Partner._onChanges = {
        p: function () {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_data_cell")).toEqual(["first record", "second record", "aaa"]);

    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_selected_row .o_field_widget[name=name] input").edit("new", {
        confirm: "blur",
    });
    contains(".o_form_view").click();
    expect(queryAllTexts(".o_data_cell")).toEqual(["new", "second record", "aaa"]);
});

test("one2many list (editable): readonly domain is evaluated", async () => {
    Partner._records[0].p = [2, 4];
    Partner._records[1].product_id = false;
    Partner._records[2].product_id = 37;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="name" readonly="not product_id"/>
                        <field name="product_id"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // switch the first row in edition
    await contains(".o_data_cell").click();
    expect(".o_selected_row .o_field_widget:eq(0)").toHaveClass("o_readonly_modifier", {
        message: "first record should have name in readonly mode",
    });
    // switch the second row in edition
    await contains(".o_data_row:not(.o_selected_row) .o_data_cell").click();
    expect(".o_selected_row .o_field_widget").not.toHaveClass("o_readonly_modifier", {
        message: "second record should not have name in readonly mode",
    });
});

test("pager of one2many field in new record", async () => {
    Partner._records[0].p = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
    });
    expect(".o_x2m_control_panel .o_pager").toHaveCount(0, {
        message: "o2m pager should be hidden",
    });

    // click to create a subrecord
    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(1);
    expect(".o_x2m_control_panel .o_pager").toHaveCount(0, {
        message: "o2m pager should be hidden",
    });
});

test.tags("desktop");
test("one2many list with a many2one", async () => {
    expect.assertions(5);

    let checkOnchange = false;
    Partner._records[0].p = [2];
    Partner._records[1].product_id = 37;
    Partner._onChanges.p = () => {};
    Partner._views.form = '<form><field name="product_id"/></form>';
    onRpc("onchange", (args) => {
        if (checkOnchange) {
            expect(args.args[1].p).toEqual([[0, args.args[1].p[0][1], { product_id: 41 }]], {
                message: "should trigger onchange with correct parameters",
            });
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="product_id"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_cell[data-tooltip='xphone']").toHaveCount(1);
    expect(".o_data_cell[data-tooltip='xpad']").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a").click();

    checkOnchange = true;
    await clickFieldDropdown("product_id");
    await contains('div[name="product_id"] .o_input_dropdown li:eq(1)').click();

    await contains(".modal .modal-footer button").click();
    expect(".o_data_cell[data-tooltip='xphone']").toHaveCount(1);
    expect(".o_data_cell[data-tooltip='xpad']").toHaveCount(1);
});

test.tags("desktop");
test("one2many list with inline form view", async () => {
    expect.assertions(5);

    Partner._records[0].p = [];
    onRpc("web_save", (args) => {
        expect(args.args[1].p).toEqual([
            [
                0,
                args.args[1].p[0][1],
                {
                    foo: "My little Foo Value",
                    int_field: 123,
                    product_id: 41,
                },
            ],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        // don't remove foo field in sub tree view, it is useful to make sure
        // the foo fieldwidget does not crash because the foo field is not in the form view
        arch: `
            <form>
                <field name="p">
                    <form>
                        <field name="product_id"/>
                        <field name="int_field"/>
                    </form>
                    <list>
                        <field name="product_id"/>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();

    // write in the many2one field, value = 37 (xphone)
    await clickFieldDropdown("product_id");
    await press("Enter");
    await animationFrame();

    // write in the integer field
    await contains('.modal .modal-body div[name="int_field"] input').edit("123", {
        confirm: false,
    });

    // save and close
    await contains(".modal .o_form_button_save").click();

    expect(".o_data_cell[data-tooltip='xphone']").toHaveCount(1);

    // reopen the record in form view
    await contains(".o_data_cell[data-tooltip='xphone']").click();
    expect(".modal .modal-body input:eq(0)").toHaveValue("xphone");

    await contains('.modal .modal-body div[name="int_field"] input').edit("456", {
        confirm: false,
    });

    // discard
    await contains(".modal .o_form_button_cancel").click();

    // reopen the record in form view
    await contains(".o_data_cell[data-tooltip='xphone']").click();

    expect('.modal .modal-body div[name="int_field"] input').toHaveValue("123", {
        message: "should display 123 (previous change has been discarded)",
    });

    // write in the many2one field, value = 41 (xpad)
    await clickFieldDropdown("product_id");
    await contains('div[name="product_id"] .o_input_dropdown li:eq(1)').click();

    // save and close
    await contains(".modal .o_form_button_save").click();

    expect(".o_data_cell[data-tooltip='xpad']").toHaveCount(1);

    // save the record
    await clickSave();
});

test.tags("desktop");
test("one2many, edit record in dialog, save, re-edit, discard", async () => {
    Partner._records[0].p = [2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <form>
                        <field name="int_field"/>
                    </form>
                    <list>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_cell[name=int_field]").toHaveText("9");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_field_widget[name=int_field] input").toHaveValue("9");

    await contains(".modal .o_field_widget[name=int_field] input").edit("123");
    await contains(`.modal .modal-footer .o_form_button_save`).click();
    expect(".o_data_cell[name=int_field]").toHaveText("123");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_field_widget[name=int_field] input").toHaveValue("123");

    await contains(`.modal .modal-footer .o_form_button_cancel`).click();
    expect(".o_data_cell[name=int_field]").toHaveText("123");

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_field_widget[name=int_field] input").toHaveValue("123");
});

test.tags("desktop");
test("one2many list with inline form view with context with parent key", async () => {
    expect.assertions(2);

    Partner._records[0].p = [2];
    Partner._records[0].product_id = 41;
    Partner._records[1].product_id = 37;
    onRpc("name_search", (args) => {
        expect(args.kwargs.context.partner_foo).toBe("yop", {
            message: "should have correctly evaluated parent foo field",
        });
        expect(args.kwargs.context.lalala).toBe(41, {
            message: "should have correctly evaluated parent product_id field",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="foo"/>
                    <field name="product_id"/>
                    <field name="p">
                        <form>
                            <field name="product_id" context="{'partner_foo':parent.foo, 'lalala': parent.product_id}"/>
                        </form>
                        <list>
                            <field name="product_id"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    // open a modal
    await contains("tr.o_data_row td[data-tooltip='xphone']").click();

    // write in the many2one field
    await contains(".modal .o_field_many2one input").click();
});

test.tags("desktop");
test("value of invisible x2many fields is correctly evaluated in context", async () => {
    expect.assertions(2);

    Partner._records[0].timmy = [12];
    Partner._records[0].p = [2, 4];
    onRpc("name_search", (args) => {
        const { p, timmy } = args.kwargs.context;
        expect(p).toEqual([2, 4]);
        expect(timmy).toEqual([12]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="product_id" context="{'p': p, 'timmy': timmy}"/>
                    <field name="p" invisible="1"/>
                    <field name="timmy" invisible="1"/>
                </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name=product_id] input").click();
});

test.tags("desktop");
test("one2many list, editable, with many2one and with context with parent key", async () => {
    expect.assertions(1);

    Partner._records[0].p = [2];
    Partner._records[1].product_id = 37;
    onRpc("name_search", (args) => {
        expect(args.kwargs.context.partner_foo).toBe("yop", {
            message: "should have correctly evaluated parent foo field",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <list editable="bottom">
                            <field name="product_id" context="{'partner_foo':parent.foo}"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    await contains("tr.o_data_row td[data-tooltip='xphone']").click();

    // trigger a name search
    await contains("table td input").click();
});

test("one2many list, multi page, with many2one and with context with parent key", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    onRpc("web_read", ({ method, model, kwargs }) => {
        if (model === "turtle") {
            expect.step("web_read turtle");
            expect(kwargs.specification.product_id.context).toEqual(
                { partner_foo: "yop" },
                { message: "should have correctly evaluated parent foo field" }
            );
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list limit="2">
                        <field name="product_id" context="{'partner_foo': parent.foo}"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_x2m_control_panel .o_pager_next").click();
    expect.verifySteps(["web_read turtle"]);
});

test("one2many list, editable, with a date in the context", async () => {
    expect.assertions(1);

    Partner._records[0].p = [2];
    Partner._records[1].product_id = 37;
    onRpc("onchange", (args) => {
        expect(args.kwargs.context.date).toBe("2017-01-25", {
            message: "should have properly evaluated date key in context",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="date"/>
                    <field name="p" context="{'date':date}">
                        <list editable="top">
                            <field name="date"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 2,
    });

    await contains(".o_field_x2many_list_row_add a").click();
});

test("one2many field with context", async () => {
    expect.assertions(2);
    onRpc("onchange", (args) => {
        expect(args.kwargs.context.turtles).toEqual([2], {
            message: "should have properly evaluated turtles key in context",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles" context="{'turtles':turtles}">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains('[name="turtle_foo"] input').edit("hammer", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();
});

test("one2many list edition, some basic functionality", async () => {
    Partner._fields.foo = fields.Char({ default: false });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect("td .o_field_widget input").toHaveCount(1);

    await contains("td .o_field_widget input").edit("a", { confirm: false });
    expect("td .o_field_widget input").toHaveCount(1, {
        message: "should not have unselected the row after edition",
    });

    await contains("td .o_field_widget input").edit("abc", { confirm: false });
    await clickSave();
    expect("td:contains('abc')").toHaveCount(1);
});

test("one2many list, the context is properly evaluated and sent", async () => {
    expect.assertions(2);
    onRpc("onchange", (args) => {
        const context = args.kwargs.context;
        expect(context.hello).toBe("world");
        expect(context.abc).toBe(10);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="p" context="{'hello': 'world', 'abc': int_field}">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
});

test("one2many list not editable, the context is properly evaluated and sent", async () => {
    expect.assertions(4);
    Turtle._views = {
        form: '<form><field name="turtle_foo"/><field name="turtle_int" readonly="context.get(\'abc\') == 10"/></form>',
    };
    onRpc("turtle", "get_views", ({ kwargs }) => {
        const context = kwargs.context;
        expect(context).toEqual({
            allowed_company_ids: [1],
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles" context="{'hello': 'world', 'abc': int_field, 'default_turtle_int': 5}">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);
    expect(".o_readonly_modifier").toHaveCount(1);
    expect(".o_readonly_modifier").toHaveText("5");
});

test.tags("desktop");
test("one2many with many2many widget: create", async () => {
    expect.assertions(10);

    Turtle._views = {
        list: `
            <list>
                <field name="name"/>
                <field name="turtle_foo"/>
                <field name="turtle_bar"/>
                <field name="product_id"/>
            </list>`,
        search: `
            <search>
                <field name="turtle_foo"/>
                <field name="turtle_bar"/>
                <field name="product_id"/>
            </search>`,
    };

    let expectedCommand;
    onRpc("turtle", "web_save", (args) => {
        expect.step("turtle save");
    });
    onRpc("partner", "web_save", (args) => {
        expect(args.args[0][0]).toBe(1, {
            message: "should write on the partner record 1",
        });
        expect(args.args[1].turtles).toEqual(expectedCommand, {
            message: "should send only a 'LINK TO' command",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" widget="many2many">
                    <list>
                        <field name="turtle_foo"/>
                        <field name="turtle_qux"/>
                        <field name="turtle_int"/>
                        <field name="product_id"/>
                    </list>
                    <form>
                        <group>
                            <field name="turtle_foo"/>
                            <field name="turtle_bar"/>
                            <field name="turtle_int"/>
                            <field name="product_id"/>
                        </group>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".modal .o_data_row").toHaveCount(2);

    await contains(".modal .o_data_row .o_list_record_selector input").click();
    await animationFrame(); // additional render due to the change of selection (done in owl, not pure js)
    await contains(".modal .o_select_button").click();
    expectedCommand = [[4, 1]];
    await clickSave();

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal .o_data_row").toHaveCount(1);

    await contains(".modal-footer button:eq(1)").click();
    await contains('.modal .o_field_widget[name="turtle_foo"] input').edit("tototo", {
        confirm: false,
    });
    await contains('.modal .o_field_widget[name="turtle_int"] input').edit(50, { confirm: false });
    await clickFieldDropdown("product_id");
    await press("Enter");
    await animationFrame();

    await contains(".modal-footer button").click();
    expect.verifySteps(["turtle save"]);

    expect(".modal").toHaveCount(0);
    expect(".o_data_row").toHaveCount(3);
    expect(queryAllTexts(".o_data_row")).toEqual(
        ["blip 1.5 9", "yop 1.5 0", "tototo 1.5 50 xphone"],
        {
            message: "should display the record values in one2many list",
        }
    );

    expectedCommand = [[4, 4]];
    await clickSave();
});

test.tags("desktop");
test("one2many with many2many widget: edition", async () => {
    expect.assertions(7);

    Turtle._views = {
        list: `
            <list>
                <field name="name"/>
                <field name="turtle_foo"/>
                <field name="turtle_bar"/>
                <field name="product_id"/>
            </list>`,
        search: `
            <search>
                <field name="turtle_foo"/>
                <field name="turtle_bar"/>
                <field name="product_id"/>
            </search>`,
    };
    onRpc("turtle", "web_save", ({ args }) => {
        expect(args[0]).toHaveLength(1);
        expect(args[1]).toEqual(
            { product_id: 37 },
            { message: "should write only the product_id on the turtle record" }
        );
    });
    onRpc("partner", "web_save", ({ args }) => {
        expect(args[0][0]).toBe(1, {
            message: "should write on the partner record 1",
        });
        expect(args[1].turtles[0][0]).toBe(4, {
            message: "should send only a 'link to' command",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" widget="many2many">
                    <list>
                        <field name="turtle_foo"/>
                        <field name="turtle_qux"/>
                        <field name="turtle_int"/>
                        <field name="product_id"/>
                    </list>
                    <form>
                        <group>
                            <field name="turtle_foo"/>
                            <field name="turtle_bar"/>
                            <field name="turtle_int"/>
                            <field name="turtle_trululu"/>
                            <field name="product_id"/>
                        </group>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click();
    expect(".modal .modal-title:eq(0)").toHaveText("Open: one2many turtle field", {
        message: "modal should use the python field string as title",
    });
    await contains(".modal .o_form_button_cancel").click();

    // edit the first one2many record
    await contains(".o_data_cell:eq(0)").click();
    await clickFieldDropdown("product_id");
    await press("Enter");
    await animationFrame();
    await contains(".modal .o_form_button_save").click();

    // add a one2many record
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_data_row:first .o_list_record_selector input:eq(0)").click();
    await animationFrame(); // wait for re-rendering because of the change of selection
    await contains(".modal .o_select_button:eq(0)").click();

    // edit the second one2many record
    await contains(".o_data_row:eq(1) .o_data_cell:eq(0)").click();
    await clickFieldDropdown("product_id");
    await press("Enter");
    await animationFrame();
    await contains(".modal .modal-footer button:first:eq(0)").click();

    await clickSave();
});

test("new record, the context is properly evaluated and sent", async () => {
    expect.assertions(2);

    Partner._fields.int_field = fields.Integer({ default: 17 });
    let n = 0;
    onRpc("onchange", (args) => {
        n++;
        if (n === 2) {
            const context = args.kwargs.context;
            expect(context.hello).toBe("world");
            expect(context.abc).toBe(17);
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="p" context="{'hello': 'world', 'abc': int_field}">
                    <list editable="top">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
});

test("parent data is properly sent on an onchange rpc", async () => {
    expect.assertions(1);
    onRpc("onchange", (args) => {
        const fieldValues = args.args[1];
        expect(fieldValues.trululu).toEqual(
            { foo: "hello", id: 1 },
            { message: "should have properly sent the parent changes" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="foo"/>
                <field name="p">
                    <list editable="top">
                        <field name="bar"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains("[name=foo] input").edit("hello", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();
});

test("parent data is properly sent on an onchange rpc (existing x2many record)", async () => {
    expect.assertions(4);

    Partner._onChanges = {
        name: function () {},
        foo: function () {},
    };
    Partner._records[0].p = [1];
    Partner._records[0].turtles = [2];

    let count = 0;
    onRpc("onchange", (args) => {
        const fieldValues = args.args[1];
        if (count === 1) {
            expect(fieldValues.trululu).toEqual({
                foo: "hello",
                id: 1,
            });
        } else if (count === 2) {
            expect(fieldValues.trululu).toEqual({
                foo: "hello",
                id: 1,
                p: [[1, 1, { name: "new val" }]],
            });
        }
        count++;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="foo"/>
                <field name="p">
                    <list editable="top">
                        <field name="name"/>
                        <field name="foo"/>
                        <field name="turtles" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(1);

    await contains("[name=foo] input").edit("hello", { confirm: false });
    await contains(".o_data_row .o_data_cell").click();
    expect(".o_data_row.o_selected_row").toHaveCount(1);

    await contains(".o_selected_row .o_field_widget[name=name] input").edit("new val", {
        confirm: false,
    });
    await contains(".o_selected_row .o_field_widget[name=foo] input").edit("new foo", {
        confirm: "blur",
    });
});

test("parent data is properly sent on an onchange rpc, new record", async () => {
    expect.assertions(2);

    Turtle._onChanges = { turtle_bar: function () {} };
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("turtle", "onchange", (args) => {
        expect(args.args[1].turtle_trululu.foo).toBe("My little Foo Value", {
            message: "should have properly sent the parent foo value",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_bar"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect.verifySteps(["get_views", "onchange", "onchange"]);
});

test("id in one2many obtained in onchange is properly set", async () => {
    Partner._onChanges.turtles = function (obj) {
        obj.turtles = [
            [4, 3],
            [1, 3, { turtle_foo: "kawa" }],
        ];
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="id"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts("tr.o_data_row .o_data_cell")).toEqual(["3", "kawa"], {
        message: "should have properly displayed id and foo field",
    });
});

test("id field in one2many in a new record", async () => {
    expect.assertions(1);
    onRpc("web_save", (args) => {
        const virtualID = args.args[1].turtles[0][1];
        expect(args.args[1].turtles).toEqual([[0, virtualID, { turtle_foo: "cat" }]], {
            message: "should send proper commands",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="id" invisible="1"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('td [name="turtle_foo"] input').edit("cat", { confirm: false });
    await clickSave();
});

test("sub form view with a required field", async () => {
    Partner._fields.foo = fields.Char({ default: null, required: true });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <form>
                        <group><field name="foo"/></group>
                    </form>
                    <list>
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal-footer button.btn-primary").click();

    expect(".modal").toHaveCount(1);
    expect(".modal label.o_field_invalid").toHaveCount(1);
});

test("one2many list with action button", async () => {
    expect.assertions(4);

    Partner._records[0].p = [2];
    mockService("action", {
        doActionButton: (params) => {
            expect(params.resId).toBe(2);
            expect(params.resModel).toBe("partner");
            expect(params.name).toBe("method_name");
            expect(params.type).toBe("object");
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="p">
                    <list>
                        <field name="foo"/>
                        <button name="method_name" type="object" icon="fa-plus"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_list_button button").click();
});

test("one2many kanban with action button", async () => {
    expect.assertions(4);

    Partner._records[0].p = [2];
    mockService("action", {
        doActionButton: (params) => {
            expect(params.resId).toBe(2);
            expect(params.resModel).toBe("partner");
            expect(params.name).toBe("method_name");
            expect(params.type).toBe("object");
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="foo"/>
                                <button name="method_name" type="object" class="fa fa-plus"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    await contains("button.oe_kanban_action").click();
});

test("one2many without inline tree arch", async () => {
    Partner._records[0].turtles = [2, 3];
    Turtle._views = {
        list: `
            <list>
                <field name="turtle_bar"/>
                <field name="name"/>
                <field name="partner_ids"/>
            </list>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        // should not call loadViews for the field with many2many_tags widget,
        // nor for the invisible field
        arch: `
            <form>
                <group>
                    <field name="p" widget="many2many_tags"/>
                    <field name="turtles"/>
                    <field name="timmy" invisible="1"/>
                </group>
            </form>`,
        resId: 1,
    });

    expect('.o_field_widget[name="turtles"] .o_list_renderer').toHaveCount(1, {
        message: "should display one2many list view in the modal",
    });

    expect(".o_data_row").toHaveCount(2);
});

test.tags("desktop");
test("many2one and many2many in one2many", async () => {
    expect.assertions(8);

    Turtle._records[1].product_id = 37;
    Partner._records[0].turtles = [2, 3];
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual(
            [
                [
                    1,
                    2,
                    {
                        partner_ids: [
                            [3, 4],
                            [4, 1],
                        ],
                        product_id: 41,
                    },
                ],
            ],
            { message: "generated commands should be correct" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="turtles">
                        <list editable="top">
                            <field name="name"/>
                            <field name="product_id"/>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row .o_list_many2one").toHaveText("xphone");
    expect('.o_data_row td div[name="partner_ids"] .badge').toHaveCount(2);

    // edit the m2m of first row
    await contains(".o_list_renderer tbody td").click();

    expect(queryAllTexts(".o_selected_row .o_field_many2many_tags .badge")).toEqual([
        "second record",
        "aaa",
    ]);

    // remove a tag
    await contains(".o_selected_row .o_field_many2many_tags .badge .o_delete:eq(1)").click();

    expect(queryAllTexts(".o_selected_row .o_field_many2many_tags .badge")).toEqual([
        "second record",
    ]);
    // add a tag
    await contains('div[name="partner_ids"] input').click();
    await contains('div[name="partner_ids"] .o_input_dropdown li').click(); // xpad

    expect(queryAllTexts(".o_selected_row .o_field_many2many_tags .badge")).toEqual([
        "second record",
        "first record",
    ]);

    // edit the m2o of first row
    await clickFieldDropdown("product_id");
    await contains('div[name="product_id"] .o_input_dropdown li:eq(1)').click(); // xpad

    expect(".o_selected_row .o_field_many2one input").toHaveValue("xpad");

    // save (should correctly generate the commands)
    await clickSave();
});

test("many2manytag in one2many, onchange, some modifiers, and more than one page", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    Partner._onChanges.turtles = function () {};
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top" limit="2">
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags" readonly="turtle_foo == 'a'"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(2);

    await contains(".o_list_record_remove").click();
    expect(".o_data_row").toHaveCount(2);

    await contains(".o_list_record_remove").click();
    expect(".o_data_row").toHaveCount(1);

    expect.verifySteps([
        "get_views", // main form view
        "web_read", // initial read on partner
        "web_read", // after first delete, read on turtle (to fetch 3rd record)
        "onchange", // after first delete, onchange on field turtles
        "onchange", // onchange after second delete
    ]);
});

test.tags("desktop");
test("onchange many2many in one2many list editable", async () => {
    Product._records.push({
        id: 1,
        name: "xenomorphe",
    });

    Turtle._onChanges = {
        product_id: function (rec) {
            if (rec.product_id === 41) {
                rec.partner_ids = [[4, 1]];
            } else if (rec.product_id === 37) {
                rec.partner_ids = [[4, 2]];
            }
        },
    };
    let enableOnchange = false;
    const partnerOnchange = function (rec) {
        if (!enableOnchange) {
            return;
        }
        rec.turtles = [
            [
                0,
                0,
                {
                    name: "new line",
                    product_id: [37, "xphone"],
                    partner_ids: [[4, 1]],
                },
            ],
            [
                1,
                rec.turtles[0][1],
                {
                    product_id: [1, "xenomorphe"],
                    partner_ids: rec.turtles[0][2].partner_ids.length
                        ? [
                              [3, 1],
                              [4, 2],
                          ]
                        : [[4, 2]],
                },
            ],
        ];
    };

    Partner._onChanges = {
        int_field: partnerOnchange,
        turtles: partnerOnchange,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="name"/>
                            <field name="product_id"/>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </list>
                    </field>
                </group>
            </form>`,
    });

    // add new line (first, xpad)
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="name"] input').edit("first", { confirm: false });
    await clickFieldDropdown("product_id");
    await contains('div[name="product_id"] .o_input_dropdown li:eq(1)').click(); // xpad

    expect(".o_field_many2many_tags .o_tags_input").toHaveCount(1, {
        message: "should display the line in editable mode",
    });
    expect(".o_field_many2one input").toHaveValue("xpad");
    expect(".o_field_many2many_tags .o_tag_badge_text").toHaveText("first record");
    expect(".o_data_cell .o_required_modifier input").toHaveValue("xpad");

    await contains('div[name="int_field"] input').click();

    expect(".o_field_many2many_tags input.o_input").toHaveCount(0, {
        message: "should display the tag in readonly",
    });
    // enable the many2many onchange and generate it
    enableOnchange = true;
    await contains('div[name="int_field"] input').edit("10");

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "first",
        "xenomorphe",
        "second record",
        "new line",
        "xphone",
        "first record",
    ]);

    // disable the many2many onchange
    enableOnchange = false;

    // remove and start over
    await contains(".o_list_record_remove button").click();
    await contains(".o_list_record_remove button").click();

    // enable the many2many onchange
    enableOnchange = true;
    // add new line (first, xenomorphe)
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="name"] input').edit("first", { confirm: false });
    await clickFieldDropdown("product_id");
    await contains('div[name="product_id"] .o_input_dropdown li:eq(2)').click(); // xenomorphe

    expect(".o_field_many2many_tags .o_tags_input").toHaveCount(1, {
        message: "should display the line in editable mode",
    });
    expect('div[name="product_id"] input').toHaveValue("xenomorphe");
    expect(".o_field_many2many_tags .o_tag_badge_text:eq(0)").toHaveText("second record");

    // put list in readonly mode
    await contains('div[name="int_field"] input').click();

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "first",
        "xenomorphe",
        "second record",
        "new line",
        "xphone",
        "first record",
    ]);

    expect(".o_field_many2many_tags input.o_input").toHaveCount(0, {
        message: "should display the tag in readonly",
    });

    await contains('div[name="int_field"] input').edit("10");

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "first",
        "xenomorphe",
        "second record",
        "new line",
        "xphone",
        "first record",
    ]);

    await clickSave();

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "first",
        "xenomorphe",
        "second record",
        "new line",
        "xphone",
        "first record",
    ]);
});

test.tags("desktop");
test("load view for x2many in one2many", async () => {
    Turtle._records[1].product_id = 37;
    Partner._records[0].turtles = [2, 3];
    Partner._records[2].turtles = [1, 3];
    Partner._views = {
        list: `
            <list>
                <field name="name"/>
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="turtles">
                        <form>
                            <group>
                                <field name="product_id"/>
                                <field name="partner_ids"/>
                            </group>
                        </form>
                        <list>
                            <field name="name"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(2);

    await contains(".o_data_row td").click();

    expect('.modal div[name="partner_ids"] .o_list_renderer').toHaveCount(1);
});

test.tags("desktop");
test("one2many (who contains a one2many) with list view and without form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form edit="0">
                    <group>
                        <field name="turtles">
                            <list>
                                <field name="partner_ids"/>
                            </list>
                            <form>
                                <field name="turtle_foo"/>
                            </form>
                        </field>
                    </group>
                </form>`,
        resId: 1,
    });

    await contains(".o_data_row td").click();

    expect('.modal div[name="turtle_foo"]').toHaveText("blip");
});

test.tags("desktop");
test("one2many with x2many in form view (but not in list view)", async () => {
    expect.assertions(1);

    // avoid error when saving the edited related record (because the
    // related x2m field is unknown in the inline list view)
    // also ensure that the changes are correctly saved
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual([
            [
                1,
                2,
                {
                    partner_ids: [[4, 1]],
                },
            ],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list>
                            <field name="turtle_foo"/>
                        </list>
                        <form>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </form>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td").click(); // edit first record

    await contains('div[name="partner_ids"] input').click();
    await contains('div[name="partner_ids"] .o_input_dropdown li').click();

    // add a many2many tag and save
    await contains(".modal .o_field_many2many_tags input").edit("test", { confirm: false });

    await contains(".modal .modal-footer .btn-primary").click(); // save

    await clickSave();
});

test.tags("desktop");
test("many2many list in a one2many opened by a many2one", async () => {
    expect.assertions(1);

    Turtle._records[1].turtle_trululu = 2;
    Partner._views = { form: '<form><field name="timmy"/></form>' };
    PartnerType._views = {
        list: '<list editable="bottom"><field name="name"/></list>',
        search: "<search></search>",
    };
    onRpc("/web/dataset/call_kw/partner/get_formview_id", () => false);
    onRpc("web_save", (args) => {
        expect(args.args[1].timmy).toEqual([[4, 12]], {
            message: "should properly add id",
        });
    });
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_trululu"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // edit the first partner in the one2many partner form view
    await contains(".o_data_row td.o_data_cell").click();
    // open form view for many2one
    await contains(".o_external_button").click();

    // click on add, to add a new partner in the m2m
    await contains(".modal:eq(1) .o_field_x2many_list_row_add a").click();

    // select the PartnerType 'gold' (this closes the 3rd modal)
    await contains(".o_dialog:not(.o_inactive_modal) td.o_data_cell").click(); // select gold

    // confirm the changes in the modal
    await contains(".modal:eq(1) .o_form_button_save").click();

    await clickSave();
});

test("nested x2many default values", async () => {
    Partner._fields.turtles = fields.One2many({
        string: "one2many turtle field",
        relation: "turtle",
        relation_field: "turtle_trululu",
        default: [
            [0, 0, { partner_ids: [[4, 4]] }],
            [0, 0, { partner_ids: [[4, 1]] }],
        ],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".o_field_x2many_list .o_data_row").toHaveCount(2);
    expect('.o_field_x2many_list .o_field_many2many_tags[name="partner_ids"] .badge').toHaveCount(
        2
    );
    expect(
        queryAllTexts(
            '.o_field_x2many_list .o_field_many2many_tags[name="partner_ids"] .o_tag_badge_text'
        )
    ).toEqual(["aaa", "first record"]);
});

test("nested x2many (inline form view) and _onChanges", async () => {
    expect.assertions(8);
    Partner._onChanges.bar = function (obj) {
        if (!obj.bar) {
            obj.p = [
                [
                    0,
                    0,
                    {
                        turtles: [
                            [
                                0,
                                0,
                                {
                                    turtle_foo: "new turtle",
                                },
                            ],
                        ],
                    },
                ],
            ];
        }
    };
    onRpc("onchange", (args) => {
        expect(args.args[3]).toEqual({
            bar: {},
            display_name: {},
            p: {
                fields: {
                    turtles: {
                        fields: {
                            turtle_foo: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p">
                    <list>
                        <field name="turtles"/>
                    </list>
                    <form>
                        <field name="turtles">
                            <list>
                                <field name="turtle_foo"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveText("1 record");

    await contains(".o_data_row td").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_data_row").toHaveCount(1);
    expect(".modal .o_form_view .o_data_row").toHaveText("new turtle");
});

test("nested x2many (non inline views and no widget on inner x2many in list)", async () => {
    Partner._records[0].p = [1];
    Partner._views = {
        list: `
            <list>
                <field name="turtles"/>
            </list>`,
        form: `
            <form>
                <field name="turtles" widget="many2many_tags"/>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="p"/></form>',
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveText("1 record");

    await contains(".o_data_row td").click();

    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_field_many2many_tags .badge").toHaveCount(1);
    expect(".modal .o_field_many2many_tags").toHaveText("donatello");
});

test("one2many (who contains name) with list view and without form view", async () => {
    Turtle._views = { form: '<form><field name="turtle_foo"/></form>' };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form edit="0">
                <group>
                    <field name="turtles">
                        <list>
                            <field name="name"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td").click();

    expect('.modal div[name="turtle_foo"]').toHaveText("blip");
});

test("open a record in a one2many list (mode 'readonly') with a notebook", async () => {
    Turtle._views = {
        form: `
            <form>
                <notebook>
                    <page string="Yop">
                        <field name="name">
                        </field>
                    </page>
            </notebook>
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_notebook_headers").toHaveCount(1);
    expect(".modal .o_form_view .o_notebook_headers").toHaveText("Yop");
});

test("one2many field with virtual ids", async () => {
    Partner._views = { form: '<form><field name="foo"/></form>' };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <notebook>
                            <page>
                                <field name="p" mode="kanban">
                                    <kanban>
                                        <templates>
                                            <t t-name="card">
                                                <field name="id" class="o_test_id"/>
                                                <field name="foo" class="o_test_foo"/>
                                            </t>
                                        </templates>
                                    </kanban>
                                </field>
                            </page>
                        </notebook>
                    </group>
                </sheet>
            </form>`,
        resId: 4,
    });

    expect(".o_field_widget .o_kanban_renderer").toHaveCount(1, {
        message: "should have one inner kanban view for the one2many field",
    });
    expect(".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(
        0,
        { message: "should not have kanban records yet" }
    );

    // create a new kanban record
    await contains(".o_field_widget .o-kanban-button-new").click();

    // save & close the modal
    expect(".modal-content .o_field_widget input").toHaveValue("My little Foo Value", {
        message: "should already have the default value for field foo",
    });
    await contains(".modal .o_form_button_save").click();

    expect(".o_field_widget .o_kanban_renderer").toHaveCount(1, {
        message: "should have one inner kanban view for the one2many field",
    });
    expect(".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(
        1,
        { message: "should now have one kanban record" }
    );
    expect(
        ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
    ).toHaveText("", { message: "should not have a value for the id field" });
    expect(
        ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
    ).toHaveText("My little Foo Value", { message: "should have a value for the foo field" });

    // save the view to force a create of the new record in the one2many
    await clickSave();
    expect(".o_field_widget .o_kanban_renderer").toHaveCount(1, {
        message: "should have one inner kanban view for the one2many field",
    });
    expect(".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(
        1,
        { message: "should now have one kanban record" }
    );
    expect(
        ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
    ).toHaveText("5", { message: "should now have a value for the id field" });
    expect(
        ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
    ).toHaveText("My little Foo Value", { message: "should still have a value for the foo field" });
});

test("one2many field with virtual ids with kanban button", async () => {
    expect.assertions(23);

    Partner._records[0].p = [4];
    onRpc("web_save", (args) => {
        expect.step(args.method);
        expect(args.args[1].p).toHaveLength(1);
        const command = args.args[1].p[0];
        expect(command[0]).toBe(0);
        expect(command[2]).toEqual({
            foo: "My little Foo Value",
        });
    });
    mockService("action", {
        doActionButton: (params) => {
            const { name, resModel, resId } = params;
            expect.step(`${name}_${resModel}_${resId}`);
            params.onClose();
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" mode="kanban">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="foo"/>
                                <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_warn" string="button_warn" warn="warn" />
                                <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_disabled" string="button_disabled" />
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    // 1. Define all css selector
    const oKanbanView = ".o_field_widget .o_kanban_renderer";
    const oKanbanRecordActive = oKanbanView + " .o_kanban_record:not(.o_kanban_ghost)";
    const oAllKanbanButton = oKanbanRecordActive + " button";
    const btn1 = oKanbanRecordActive + ":eq(0) button";
    const btn2 = oKanbanRecordActive + ":eq(1) button";
    const btn1Warn = btn1 + '[name="button_warn"]';
    const btn1Disabled = btn1 + '[name="button_disabled"]';
    const btn2Warn = btn2 + '[name="button_warn"]';
    const btn2Disabled = btn2 + '[name="button_disabled"]';

    // check if we already have one kanban card
    expect(oKanbanView).toHaveCount(1, {
        message: "should have one inner kanban view for the one2many field",
    });
    expect(oKanbanRecordActive).toHaveCount(1, { message: "should have one kanban records yet" });

    // we have 2 buttons
    expect(oAllKanbanButton).toHaveCount(2);

    // disabled ?
    expect(oAllKanbanButton + "[disabled]").toHaveCount(0, {
        message: "should not have button type object disabled",
    });

    // click on the button
    await contains(btn1Disabled).click();
    expect.verifySteps(["button_disabled_partner_4"]);

    await contains(btn1Warn).click();
    expect.verifySteps(["button_warn_partner_4"]);

    // click on existing buttons
    await contains(btn1Disabled).click();
    expect.verifySteps(["button_disabled_partner_4"]);

    await contains(btn1Warn).click();
    expect.verifySteps(["button_warn_partner_4"]);

    // create new kanban record
    await contains(".o_field_widget .o-kanban-button-new").click();

    // save & close the modal
    expect(".modal-content .o_field_widget input").toHaveValue("My little Foo Value", {
        message: "should already have the default value for field foo",
    });
    await contains(".modal .o_form_button_save").click();

    // check new item
    expect(oAllKanbanButton).toHaveCount(4);
    expect(btn1).toHaveCount(2);
    expect(btn2).toHaveCount(2);
    expect(oAllKanbanButton + "[disabled]").toHaveCount(0, {
        message: "should have 1 button type object disabled",
    });

    expect(btn2Disabled).toBeEnabled();
    expect(btn2Warn).toBeEnabled();

    expect(btn2Warn).toHaveAttribute("warn", "warn", {
        message: "Should have a button type object with warn attr in area 2",
    });

    // click all buttons
    await contains(btn1Disabled).click();
    expect.verifySteps(["web_save", "button_disabled_partner_4"]);
    await contains(btn1Warn).click();
    await contains(btn2Disabled).click();
    await contains(btn2Warn).click();
    expect.verifySteps([
        "button_warn_partner_4",
        "button_disabled_partner_5",
        "button_warn_partner_5",
    ]);

    // save the form
    expect(".o_form_saved").toHaveCount(1);

    // click all buttons
    await contains(btn1Disabled).click();
    await contains(btn1Warn).click();
    await contains(btn2Disabled).click();
    await contains(btn2Warn).click();

    // should have clicked once on every button
    expect.verifySteps([
        "button_disabled_partner_4",
        "button_warn_partner_4",
        "button_disabled_partner_5",
        "button_warn_partner_5",
    ]);
});

test("focusing fields in one2many list", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                            <field name="turtle_int"/>
                        </list>
                    </field>
                </group>
                <field name="foo"/>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td").click();
    expect('[name="turtle_foo"] input').toBeFocused();

    await press("Tab");
    await animationFrame();
    expect('[name="turtle_int"] input').toBeFocused();
});

test("one2many list editable = top", async () => {
    expect.assertions(5);
    Turtle._fields.turtle_foo = fields.Char({ default: "default foo turtle" });
    onRpc("web_save", (args) => {
        const commands = args.args[1].turtles;
        expect(commands).toEqual([[0, commands[0][1], { turtle_foo: "default foo turtle" }]]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(1);

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(2);
    expect("tr.o_data_row input").toHaveValue("default foo turtle", {
        message: "first row should be the new value",
    });
    expect("tr.o_data_row:eq(0)").toHaveClass("o_selected_row");

    await clickSave();
});

test("one2many list editable = bottom", async () => {
    expect.assertions(5);
    Turtle._fields.turtle_foo = fields.Char({ default: "default foo turtle" });
    onRpc("web_save", (args) => {
        const commands = args.args[1].turtles;
        expect(commands).toEqual([[0, commands[0][1], { turtle_foo: "default foo turtle" }]]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(2);
    expect("tr.o_data_row input").toHaveValue("default foo turtle", {
        message: "second row should be the new value",
    });
    expect("tr.o_data_row:eq(1)").toHaveClass("o_selected_row");

    await clickSave();
});

test("one2many list editable - should properly unselect the list field after shift+tab", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <group>
                    <field name="name"/>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                            <field name="turtle_bar" optional="hide"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td:first-child").click();
    expect(".o_selected_row").toHaveCount(1);
    const events = await press("Shift+Tab");
    await animationFrame();
    expect(".o_selected_row").toHaveCount(0, { message: "list should not be in edition" });
    // We also check the event is not default prevented, to make sure that the
    // event flows and selection goes to the previous field.
    expect(events[0].defaultPrevented).toBe(false);
    expect(events[1].defaultPrevented).toBe(false);
});

test("one2many list editable - should not allow tab navigation focus on the optional field toggler", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <group>
                    <field name="name"/>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                            <field name="turtle_bar" optional="hide"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });
    expect(".o_optional_columns_dropdown .dropdown-toggle").toHaveProperty("tabIndex", -1);
});

test('one2many list edition, no "Remove" button in modal', async () => {
    Partner._fields.foo = fields.Char({ default: false });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="foo"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(0);

    // Discard a modal
    await contains(".modal-footer .btn-secondary").click();
});

test('x2many fields use their "mode" attribute', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field mode="kanban" name="turtles">
                        <list>
                            <field name="turtle_foo"/>
                        </list>
                        <kanban>
                            <templates>
                                <t t-name="card">
                                    <field name="turtle_int"/>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect(".o_field_one2many .o_field_x2many_kanban").toHaveCount(1, {
        message: "should have rendered a kanban view",
    });
});

test("one2many list editable, onchange and required field", async () => {
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    let intFieldVal = 0;
    Partner._onChanges = {
        turtles: function (obj) {
            obj.int_field = intFieldVal;
        },
    };
    Partner._records[0].int_field = 0;
    Partner._records[0].turtles = [];
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_int"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect('.o_field_widget[name="int_field"] input').toHaveValue("0");

    intFieldVal = 1;
    await contains(".o_field_x2many_list_row_add a").click();
    expect('.o_field_widget[name="int_field"] input').toHaveValue("0");
    expect.verifySteps(["get_views", "web_read", "onchange"]);

    await contains('.o_field_widget[name="turtle_foo"] input').edit("some text", {
        confirm: "blur",
    });
    expect.verifySteps(["onchange"]);
    expect('.o_field_widget[name="int_field"] input').toHaveValue("1");
});

test.tags("desktop");
test("one2many list editable: trigger onchange when row is valid", async () => {
    // should omit require fields that aren't in the view as they (obviously)
    // have no value, when checking the validity of required fields
    // shouldn't consider numerical fields with value 0 as unset
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    Turtle._fields.turtle_bar = fields.Boolean({ required: true });
    Turtle._fields.turtle_int = fields.Integer({ required: true, default: 0 }); // required int field (default 0)
    Turtle._fields.partner_ids = fields.Many2many({ relation: "partner", required: true }); // required many2many
    let intFieldVal = 0;
    Partner._onChanges = {
        turtles: function (obj) {
            obj.int_field = intFieldVal;
        },
    };
    Partner._records[0].int_field = 0;
    Partner._records[0].turtles = [];

    Turtle._views = {
        list: `
            <list editable="top">
                <field name="turtle_qux"/>
                <field name="turtle_bar"/>
                <field name="turtle_int"/>
                <field name="turtle_foo"/>
                <field name="partner_ids" widget="many2many_tags"/>
            </list>`,
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles"/>
            </form>`,
        resId: 1,
    });

    expect('.o_field_widget[name="int_field"] input').toHaveValue("0", {
        message: "int_field should start with value 0",
    });

    intFieldVal = 1;
    // add a new row (which is invalid at first)
    await contains(".o_field_x2many_list_row_add a").click();
    expect('.o_field_widget[name="int_field"] input').toHaveValue("0", {
        message: "int_field should still be 0 (no onchange should have been done yet)",
    });
    expect.verifySteps(["get_views", "web_read", "onchange"]);

    // fill turtle_foo field
    await contains('.o_field_widget[name="turtle_foo"] input').edit("some text", {
        confirm: false,
    });
    expect('.o_field_widget[name="int_field"] input').toHaveValue("0", {
        message: "int_field should still be 0 (no onchange should have been done yet)",
    });
    // no onchange should have been applied
    expect.verifySteps([]);

    // fill partner_ids field with a tag (all required fields will then be set)
    await selectFieldDropdownItem("partner_ids", "first record");

    expect('.o_field_widget[name="int_field"] input').toHaveValue("1", {
        message: "int_field should now be 1 (the onchange should have been done",
    });
    expect.verifySteps(["name_search", "web_read", "onchange"]);
});

test("one2many list editable: 'required' modifiers is properly working", async () => {
    Partner._onChanges = {
        turtles: function (obj) {
            obj.int_field = 44;
        },
    };

    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo" required="1"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect('.o_field_widget[name="int_field"] input').toHaveValue("10");

    await contains(".o_field_x2many_list_row_add a").click();
    expect('.o_field_widget[name="int_field"] input').toHaveValue("10");

    // fill turtle_foo field
    await contains('.o_field_widget[name="turtle_foo"] input').edit("some text");

    expect('.o_field_widget[name="int_field"] input').toHaveValue("44");
});

test("one2many list editable: 'required' modifiers is properly working, part 2", async () => {
    Partner._onChanges = {
        turtles: function (obj) {
            obj.int_field = 44;
        },
    };

    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_int"/>
                        <field name="turtle_foo" required='turtle_int == 0'/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect('.o_field_widget[name="int_field"] input').toHaveValue("10");

    await contains(".o_field_x2many_list_row_add a").click();
    expect('.o_field_widget[name="int_field"] input').toHaveValue("10");

    // fill turtle_int field
    await contains('.o_field_widget[name="turtle_int"] input').edit("1");
    expect('.o_field_widget[name="int_field"] input').toHaveValue("44");
});

test.tags("desktop");
test("one2many list editable: add new line before onchange returns", async () => {
    // If the user adds a new row (with a required field with onchange), selects
    // a value for that field, then adds another row before the onchange returns,
    // the editable list must wait for the onchange to return before trying to
    // unselect the first row, otherwise it will be detected as invalid.
    Turtle._onChanges = {
        turtle_trululu: function () {},
    };

    let def;
    onRpc("onchange", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_trululu" required="1"/>
                    </list>
                </field>
            </form>`,
    });

    // add a first line but hold the onchange back
    await contains(".o_field_x2many_list_row_add a").click();
    def = new Deferred();
    expect(".o_data_row").toHaveCount(1);
    await clickFieldDropdown("turtle_trululu");
    await press("Enter");
    await animationFrame();

    // try to add a second line and check that it is correctly waiting
    // for the onchange to return
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(0);
    expect(".o_field_invalid").toHaveCount(0);
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveClass("o_selected_row");

    // resolve the onchange promise
    def.resolve();
    await animationFrame();
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:first").not.toHaveClass("o_selected_row");
});

test("editable list: multiple clicks on Add an item do not create invalid rows", async () => {
    Turtle._onChanges = {
        turtle_trululu: function () {},
    };

    let def;
    onRpc("onchange", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_trululu" required="1"/>
                    </list>
                </field>
            </form>`,
    });
    def = new Deferred();
    // click twice to add a new line
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(0);

    // resolve the onchange promise
    def.resolve();
    await animationFrame();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveClass("o_selected_row");
});

test("editable list: value reset by an onchange", async () => {
    // this test reproduces a subtle behavior that may occur in a form view:
    // the user adds a record in a one2many field, and directly clicks on a
    // datetime field of the form view which has an onchange, which totally
    // erases the value from the one2many (command 2 + command 0). The handler
    // that switches the edited row to readonly is then called after the
    // new value of the one2many field is applied (the one returned by the
    // onchange), so the row that must go to readonly doesn't exist anymore.
    Partner._onChanges = {
        datetime: function (obj) {
            if (obj.turtles.length) {
                obj.turtles = [
                    [2, obj.turtles[0][1]],
                    [0, 0, { name: "new" }],
                ];
            }
        },
    };

    let def;
    onRpc("onchange", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime"/>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    // trigger the two _onChanges
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_data_row .o_field_widget input").edit("a name", { confirm: false });
    def = new Deferred();
    await contains(".o_field_datetime .o_input").edit("04/27/2022 14:08:52", { confirm: "blur" });

    // resolve the onchange promise
    def.resolve();
    await animationFrame();

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_data_cell").toHaveText("new");
});

test("editable list: onchange that returns a warning", async () => {
    Turtle._onChanges = {
        name: function () {},
    };

    const warning = {
        title: "Warning",
        message: "You must first select a partner",
    };
    onRpc("onchange", (args) => {
        expect.step(args.method);
        return {
            value: {},
            warning,
        };
    });
    mockService("notification", {
        add: (message, params) => {
            expect.step(params.type);
            expect(message).toBe(warning.message);
            expect(params.title).toBe(warning.title);
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a line (this should trigger an onchange and a warning)
    await contains(".o_field_x2many_list_row_add a").click();

    // check if 'Add an item' still works (this should trigger an onchange
    // and a warning again)
    await contains(".o_field_x2many_list_row_add a").click();

    expect.verifySteps(["onchange", "warning", "onchange", "warning"]);
});

test("editable list: contexts are correctly sent", async () => {
    expect.assertions(4);

    Partner._records[0].timmy = [12];
    serverState.userContext = { someKey: "some value" };
    onRpc("partner", "web_read", ({ kwargs }) => {
        expect(kwargs.context).toEqual(
            {
                allowed_company_ids: [1],
                active_field: 2,
                bin_size: true,
                someKey: "some value",
                uid: 7,
                lang: "en",
                tz: "taht",
            },
            { message: "read partner context" }
        );
        expect(kwargs.specification.timmy.context).toEqual({ key2: "hello" });
    });
    onRpc("web_save", (args) => {
        expect(args.kwargs.context).toEqual(
            {
                allowed_company_ids: [1],
                active_field: 2,
                someKey: "some value",
                uid: 7,
                lang: "en",
                tz: "taht",
            },
            { message: "read partner context" }
        );
        expect(args.kwargs.specification.timmy.context).toEqual({ key2: "hello" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="timmy" context="{'key': foo, 'key2': 'hello'}">
                    <list editable="top">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        context: { active_field: 2 },
    });
    await contains(".o_data_cell").click();
    await contains(".o_field_widget[name=name] input").edit("abc", { confirm: false });
    await clickSave();
});

test("contexts of nested x2manys are correctly sent (add line)", async () => {
    expect.assertions(4);
    Partner._fields.timmy = fields.Many2many({
        relation: "partner.type",
        string: "pokemon",
        default: [[4, 12]],
    });
    serverState.userContext = { someKey: "some value" };
    onRpc("onchange", (args) => {
        expect(args.kwargs.context).toEqual(
            {
                allowed_company_ids: [1],
                active_field: 2,
                someKey: "some value",
                uid: 7,
                lang: "en",
                tz: "taht",
            },
            { message: "onchange context" }
        );
        expect(args.args[3].timmy.context).toEqual({
            key: "yop",
            key2: "hello",
        });
    });
    onRpc("partner", "web_read", (args) => {
        expect(args.kwargs.context).toEqual(
            {
                allowed_company_ids: [1],
                active_field: 2,
                bin_size: true,
                someKey: "some value",
                uid: 7,
                lang: "en",
                tz: "taht",
            },
            { message: "read timmy context" }
        );
        expect(args.kwargs.specification.p.fields.timmy.context).toEqual({
            key2: "hello",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="p">
                    <list editable="top">
                        <field name="name"/>
                        <field name="timmy" context="{'key': parent.foo, 'key2': 'hello'}" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        context: { active_field: 2 },
    });

    await contains(".o_field_x2many_list_row_add a").click();
});

test("nested x2manys with context referencing parent record", async () => {
    expect.assertions(3);

    Partner._records[0].p = [2];

    let onchangeNb = 0;
    onRpc("onchange", (args) => {
        onchangeNb++;
        if (onchangeNb === 1) {
            expect(args.args[3].p.context).toEqual({ parent_foo: "yop" });
        } else {
            expect(args.kwargs.context.parent_foo).toBe("yop");
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="p" context="{'parent_foo': parent.foo}">
                            <list>
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .o_field_x2many_list_row_add a").click();
});

test("resetting invisible one2manys", async () => {
    Partner._records[0].turtles = [];
    Partner._onChanges.foo = function (obj) {
        obj.turtles = [[5], [4, 1]];
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles" invisible="1"/>
            </form>`,
        resId: 1,
    });
    await contains('[name="foo"] input').edit("abcd", { confirm: "blur" });
    expect.verifySteps(["get_views", "web_read", "onchange"]);
});

test("one2many: onchange that returns unknown field in list, but not in form", async () => {
    expect.assertions(6);
    Partner._onChanges = {
        name: function (obj) {
            obj.p = [[0, 0, { name: "new", timmy: [[4, 12]] }]];
        },
    };
    onRpc("onchange", (args) => {
        expect(args.args[3]).toEqual({
            name: {},
            display_name: {},
            p: {
                fields: {
                    name: {},
                    timmy: {
                        fields: {
                            display_name: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <field name="timmy" widget="many2many_tags"/>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect('.o_field_widget[name="timmy"]').toHaveCount(0);

    await contains(".o_data_row td").click();
    expect('.modal .o_field_many2many_tags[name="timmy"]').toHaveCount(1);
    expect('.modal .o_field_many2many_tags[name="timmy"] .badge').toHaveCount(1);
    expect(queryAllTexts('.modal .o_field_many2many_tags[name="timmy"] .o_tag_badge_text')).toEqual(
        ["gold"]
    );
});

test("multi level of nested x2manys, onchange", async () => {
    expect.assertions(7);
    Partner._records[0].p = [1];
    Partner._onChanges = {
        name: function () {},
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].p[0][2]).toEqual({
            p: [[1, 1, { name: "new name" }]],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="p" readonly="name == 'readonly'">
                    <list><field name="name"/></list>
                    <form>
                        <field name="name"/>
                        <field name="p">
                            <list><field name="name"/></list>
                            <form><field name="name"/></form>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);

    // open the dialog
    await contains(".o_data_row td").click();
    expect(".modal .o_form_editable").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(1);

    // open the o2m again, in the dialog
    await contains(".modal .o_data_row td").click();

    expect(".modal .o_form_editable").toHaveCount(2);

    // edit the name and click save modal that is on top
    await contains(".modal:eq(1) .o_field_widget[name=name] input").edit("new name", {
        confirm: false,
    });
    await contains(".modal:eq(1) .modal-footer .btn-primary").click();

    expect(".modal .o_form_editable").toHaveCount(1);

    // click save on the other modal
    await contains(".modal .modal-footer .btn-primary").click();

    expect(".modal").toHaveCount(0);

    // save the main record
    await clickSave();
});

test("onchange and required fields with override in arch", async () => {
    Partner._onChanges = {
        turtles: function () {},
    };
    Turtle._fields.turtle_foo = fields.Char({ required: true });
    Partner._records[0].turtles = [];
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int"/>
                        <field name="turtle_foo" required="0"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    // triggers an onchange on partner, because the new record is valid
    await contains(".o_field_x2many_list_row_add a").click();

    expect.verifySteps(["get_views", "web_read", "onchange", "onchange"]);
});

test("onchange on a one2many containing a one2many", async () => {
    // the purpose of this test is to ensure that the onchange specs are
    // correctly and recursively computed
    expect.assertions(1);

    Partner._onChanges = {
        p: function () {},
    };
    let checkOnchange = false;
    onRpc("onchange", (args) => {
        if (checkOnchange) {
            expect(args.args[3]).toEqual({
                display_name: {},
                p: {
                    fields: {
                        name: {},
                        p: {
                            fields: {
                                name: {},
                            },
                            limit: 40,
                            order: "",
                        },
                    },
                    limit: 40,
                    order: "",
                },
            });
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <field name="p">
                            <list editable="bottom">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_x2many_list_row_add a").click();
    await contains(".modal .o_data_cell input").edit("new record", { confirm: "blur" });
    checkOnchange = true;
    await contains(".modal .modal-footer .btn-primary").click();
});

test("editing tabbed one2many (editable=bottom)", async () => {
    expect.assertions(6);

    Partner._records[0].turtles = [];
    for (let i = 0; i < 42; i++) {
        const id = 100 + i;
        Turtle._records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
        Partner._records[0].turtles.push(id);
    }
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles[0][0]).toBe(0, {
            message: "should send a create command",
        });
        expect(args.args[1].turtles[0][2]).toEqual({ turtle_foo: "rainbow dash" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(41);
    expect("tr.o_data_row:last").toHaveClass("o_selected_row");

    await contains('.o_data_row [name="turtle_foo"] input').edit("rainbow dash", {
        confirm: false,
    });
    await clickSave();
    expect("tr.o_data_row").toHaveCount(40);

    expect.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
});

test("editing tabbed one2many (editable=bottom), again...", async () => {
    Partner._records[0].turtles = [];
    for (let i = 0; i < 9; i++) {
        const id = 100 + i;
        Turtle._records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
        Partner._records[0].turtles.push(id);
    }

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="3">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    // add a new record page 1 (this increases the limit to 4)
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_data_row [name="turtle_foo"] input').edit("rainbow dash", {
        confirm: false,
    });
    await contains(".o_x2m_control_panel .o_pager_next").click(); // page 2: 4 records
    await contains(".o_x2m_control_panel .o_pager_next").click(); // page 3: 2 records
    expect("tr.o_data_row").toHaveCount(2);
});

test("editing tabbed one2many (editable=top)", async () => {
    expect.assertions(8);

    Partner._records[0].turtles = [];
    Turtle._fields.turtle_foo = fields.Char({ default: "default foo" });
    for (let i = 0; i < 42; i++) {
        const id = 100 + i;
        Turtle._records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
        Partner._records[0].turtles.push(id);
    }
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles[0][0]).toBe(0);
        expect(args.args[1].turtles[0][2]).toEqual({ turtle_foo: "rainbow dash" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_widget[name=turtles] .o_pager_next").click();
    expect("tr.o_data_row").toHaveCount(2);

    await contains(".o_field_x2many_list_row_add a").click();
    expect("tr.o_data_row").toHaveCount(3);
    expect("tr.o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect("tr.o_data_row input").toHaveValue("default foo");

    await contains('.o_data_row [name="turtle_foo"] input').edit("rainbow dash", {
        confirm: false,
    });
    await clickSave();
    expect("tr.o_data_row").toHaveCount(40);

    expect.verifySteps(["get_views", "web_read", "web_read", "onchange", "web_save"]);
});

test.tags("desktop");
test("one2many field: change value before pending onchange returns", async () => {
    Partner._onChanges = {
        int_field: function () {},
    };
    let def;
    onRpc("onchange", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="int_field"/>
                        <field name="trululu"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    def = new Deferred();
    await contains(".o_field_widget[name=int_field] input").edit("44", { confirm: false });

    // set trululu before onchange
    await contains(".o_field_widget[name=trululu] input").edit("first", { confirm: false });
    await runAllTimers();

    // complete the onchange
    def.resolve();
    expect(".o_field_many2one input").toHaveValue("first");
    await animationFrame();
    // check name_search result
    expect(".o_field_many2one input").toHaveValue("first");
    expect(".dropdown-menu li:not(.o_m2o_dropdown_option)").toHaveCount(1);
});

test.tags("desktop");
test("focus is correctly reset after an onchange in an x2many", async () => {
    Partner._onChanges = {
        int_field: function () {},
    };

    let def;
    onRpc("onchange", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="int_field"/>
                        <button string="hello"/>
                        <field name="qux"/>
                        <field name="trululu"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    def = new Deferred();

    contains("[name=int_field] input").edit("44", { confirm: false });

    await contains(".o_field_widget[name=qux]").click();
    expect(".o_field_widget[name=qux] input").toBeFocused();

    def.resolve();
    await animationFrame();
    expect(".o_field_widget[name=qux] input").toBeFocused();

    await clickFieldDropdown("trululu");
    await press("Enter");
    await animationFrame();
    expect(".o_field_widget[name=trululu] input").toHaveValue("first record");
});

test("checkbox in an x2many that triggers an onchange", async () => {
    Partner._onChanges = {
        bar: function () {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="bar"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget[name=bar] input").toBeChecked();

    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_field_widget[name=bar] input").not.toBeChecked();
});

test("one2many with default value: edit line to make it invalid", async () => {
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [[0, false, { foo: "coucou", int_field: 5, p: [] }]],
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
    });

    // edit the line and enter an invalid value for int_field
    await contains(".o_data_row .o_data_cell:eq(1)").click();
    await contains(".o_field_widget[name=int_field] input").edit("e", { confirm: false });
    await contains(".o_form_view").click();

    expect(".o_data_row.o_selected_row").toHaveCount(1, {
        message: "line should not have been removed and should still be in edition",
    });
    expect(".modal").toHaveCount(0, { message: "a confirmation dialog should not be opened" });
    expect(".o_field_widget[name=int_field]").toHaveClass("o_field_invalid");
});

test("one2many with invalid value and click on another row", async () => {
    Partner._records[0].p = [2, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row:eq(0) .o_data_cell").click();
    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_data_row:eq(1)").not.toHaveClass("o_selected_row");

    await contains(".o_data_row [name='int_field'] input").edit("abc", { confirm: false });
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    // Stays on the invalid row
    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_data_row:eq(0) [name='int_field'] .o_field_invalid").toHaveCount(1);
    expect(".o_data_row:eq(1)").not.toHaveClass("o_selected_row");
});

test("default value for nested one2manys (coming from onchange)", async () => {
    expect.assertions(3);

    Partner._onChanges.p = function (obj) {
        obj.p = [
            [5],
            [0, 0, { turtles: [[5], [4, 1, false]] }], // link record 1 by default
        ];
    };
    onRpc("web_save", (args) => {
        expect(args.args[1].p[0][0]).toBe(0, {
            message: "should send a command 0 (CREATE) for p",
        });
        expect(args.args[1].p[0][2]).toEqual(
            { turtles: [[4, 1]] },
            { message: "should send the correct values" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list>
                            <field name="turtles"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["1 record"]);

    await clickSave();
});

test("display correct value after validation error", async () => {
    expect.assertions(5);

    function validationHandler(env, error, originalError) {
        if (originalError.data.name === "odoo.exceptions.ValidationError") {
            return true;
        }
    }
    const errorHandlerRegistry = registry.category("error_handlers");
    errorHandlerRegistry.add("validationHandler", validationHandler, { sequence: 1 });

    Partner._onChanges.turtles = function () {};
    onRpc("onchange", (args) => {
        if (args.args[1].turtles[0][2].turtle_foo === "pinky") {
            throw makeServerError({ type: "ValidationError" });
        }
    });
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles[0]).toEqual([1, 2, { turtle_foo: "foo" }], {
            message: 'should send the "good" value',
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row .o_data_cell").toHaveText("blip");

    // click and edit value to 'foo', which will trigger onchange
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_field_widget[name=turtle_foo] input").edit("foo", { confirm: false });
    await contains(".o_form_view").click();
    expect(".o_data_row .o_data_cell").toHaveText("foo");

    // click and edit value to 'pinky', which trigger a failed onchange
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_field_widget[name=turtle_foo] input").edit("pinky", { confirm: false });
    expect.errors(1);
    await contains(".o_form_view").click();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_data_row .o_data_cell").toHaveText("foo");

    // we make sure here that when we save, the values are the current
    // values displayed in the field.
    await clickSave();
});

test("propagate context to sub views without default_* keys", async () => {
    expect.assertions(4);
    onRpc("onchange", (args) => {
        expect(args.kwargs.context.flutter).toBe("shy", {
            message: "view context key should be used for every rpcs",
        });
        if (args.model === "partner") {
            expect(args.kwargs.context.default_flutter).toBe("why", {
                message: "should have default_* values in context for form view RPCs",
            });
        } else if (args.model === "turtle") {
            expect(args.kwargs.context.default_flutter).toBe(undefined, {
                message: "should not have default_* values in context for subview RPCs",
            });
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        context: {
            flutter: "shy",
            default_flutter: "why",
        },
    });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('[name="turtle_foo"] input').edit("pinky pie", { confirm: false });
    await clickSave();
});

test("nested one2manys with no widget in list and as invisible list in form", async () => {
    Partner._records[0].p = [1];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="turtles"/>
                    </list>
                    <form>
                        <field name="turtles" invisible="1"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(["1 record"]);

    await contains(".o_data_row td").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_field_one2many").toHaveCount(0);

    // Test possible caching issues
    await contains(".modal .o_form_button_cancel").click();
    await contains(".o_data_row td").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_field_one2many").toHaveCount(0);
});

test("onchange on nested one2manys", async () => {
    expect.assertions(3);

    Partner._onChanges.name = function (obj) {
        if (obj.name) {
            obj.p = [
                [
                    0,
                    0,
                    {
                        name: "test",
                        turtles: [[0, 0, { name: "test nested" }]],
                    },
                ],
            ];
        }
    };
    onRpc("web_save", (args) => {
        const commands = args.args[1].p;
        expect(commands).toEqual([
            [
                0,
                commands[0][1],
                {
                    name: "test",
                    turtles: [[0, commands[0][2].turtles[0][1], { name: "test nested" }]],
                },
            ],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="name"/>
                    <field name="p">
                        <list>
                            <field name="name"/>
                        </list>
                        <form>
                            <field name="turtles">
                                <list>
                                    <field name="name"/>
                                </list>
                            </field>
                        </form>
                    </field>
                </sheet>
            </form>`,
    });

    await contains(".o_field_widget[name=name] input").edit("trigger onchange", {
        confirm: "blur",
    });
    expect(queryAllTexts(".o_data_cell")).toEqual(["test"]);

    // open the new subrecord to check the value of the nested o2m, and to
    // ensure that it will be saved
    await contains(".o_data_cell").click();
    expect(queryAllTexts(".modal .o_data_cell")).toEqual(["test nested"]);

    await contains(".modal .modal-footer .btn-primary").click();
    await clickSave();
});

test("one2many with multiple pages and sequence field", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Partner._onChanges.turtles = function () {};
    onRpc("onchange", () => {
        return {
            value: {
                turtles: [
                    [2, 2],
                    [2, 3],
                    [4, 1, { id: 1, turtle_int: 0, turtle_foo: "yop", partner_ids: [] }],
                    [1, 1, { turtle_foo: "from onchange" }],
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="2">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                        <field name="partner_ids" invisible="1"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_list_record_remove button").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["from onchange"]);
});

test("one2many with multiple pages and sequence field, part2", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Partner._onChanges.turtles = function () {};
    onRpc("onchange", () => {
        return {
            value: {
                turtles: [
                    [2, 2],
                    [4, 1, { id: 1, turtle_int: 0, turtle_foo: "yop", partner_ids: [] }],
                    [1, 1, { turtle_foo: "from onchange id2" }],
                    [1, 3, { turtle_foo: "from onchange id3" }],
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="2">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                        <field name="partner_ids" invisible="1"/>
                    </list>
                    <form/>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_data_row .o_data_cell.o_list_char")).toEqual(["yop", "blip"]);
    await contains(".o_list_record_remove button").click();
    expect(queryAllTexts(".o_data_row .o_data_cell.o_list_char")).toEqual([
        "from onchange id3",
        "from onchange id2",
    ]);
});

test("one2many with sequence field, override default_get, bottom when inline", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Turtle._fields.turtle_int = fields.Integer({ default: 10 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    // starting condition
    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa"]);

    // click add a new line
    // save the record
    // check line is at the correct place
    const inputText = "ninja";
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('[name="turtle_foo"] input').edit(inputText, { confirm: false });
    await clickSave();

    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa", inputText]);
});

test("one2many with sequence field, override default_get, top when inline", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Turtle._fields.turtle_int = fields.Integer({ default: 10 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // starting condition
    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa"]);

    // click add a new line
    // save the record
    // check line is at the correct place
    const inputText = "ninja";
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('[name="turtle_foo"] input').edit(inputText, { confirm: false });
    await clickSave();

    expect(queryAllTexts(".o_data_row")).toEqual([inputText, "blip", "yop", "kawa"]);
});

test("one2many with sequence field, override default_get, bottom when popup", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Turtle._fields.turtle_int = fields.Integer({ default: 10 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                    <form>
                        <field name="turtle_int" invisible="1"/>
                        <field name="turtle_foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    // starting condition
    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa"]);

    // click add a new line
    // save the record
    // check line is at the correct place
    const inputText = "ninja";
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.modal [name="turtle_foo"] input').edit(inputText, { confirm: false });
    await contains(".modal .o_form_button_save").click();

    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa", inputText]);

    await clickSave();

    expect(queryAllTexts(".o_data_row")).toEqual(["blip", "yop", "kawa", inputText]);
});

test("one2many with sequence field, override default_get, not last page", async () => {
    Partner._records[0].turtles = [3, 2, 1];

    Turtle._fields.turtle_int = fields.Integer({ default: 5 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="2">
                        <field name="turtle_int" widget="handle"/>
                    </list>
                    <form>
                        <field name="turtle_int"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    // click add a new line
    // check turtle_int for new is the current max of the page
    await contains(".o_field_x2many_list_row_add a").click();
    expect('.modal [name="turtle_int"] input').toHaveValue("9");
});

test("one2many with sequence field, override default_get, last page", async () => {
    Partner._records[0].turtles = [3, 2, 1];
    Turtle._fields.turtle_int = fields.Integer({ default: 10 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="4">
                        <field name="turtle_int" widget="handle"/>
                    </list>
                    <form>
                        <field name="turtle_int"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    // click add a new line
    // check turtle_int for new is the current max of the page +1
    await contains(".o_field_x2many_list_row_add a").click();
    expect('.modal [name="turtle_int"] input').toHaveValue("22");
});

test("one2many with sequence field and text field", async () => {
    Turtle._fields.turtle_int = fields.Integer({ default: 10 });
    Turtle._fields.product_id = fields.Many2one({
        relation: "product",
        required: true,
        default: 37,
    });
    Turtle._fields.not_required_product_id = fields.Many2one({
        string: "Product",
        relation: "product",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                        <field name="not_required_product_id"/>
                        <field name="turtle_description" widget="text"/>
                    </list>
                </field>
            </form>`,
    });

    // starting condition
    expect(".o_data_cell").toHaveCount(0);

    const inputText1 = "relax";
    const inputText2 = "max";
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="turtle_foo"] input').edit(inputText1, { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="turtle_foo"] input').edit(inputText2, { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([inputText1, inputText2, ""]);

    expect(".ui-sortable-handle").toHaveCount(3);

    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr:eq(0)");

    // empty line has been discarded on the drag and drop)
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([inputText2, inputText1]);
});

test("one2many with several pages, onchange and default order", async () => {
    // This test reproduces a specific scenario where a one2many is displayed
    // over several pages, and has a default order such that a record that
    // would normally be on page 1 is actually on another page. Moreover,
    // there is an onchange on that one2many which converts all commands 4
    // (LINK_TO) into commands 1 (UPDATE), which is standard in the ORM.
    // This test ensures that the record displayed on page 2 is never fully
    // read.

    Partner._records[0].turtles = [1, 2, 3];
    Turtle._records[0].partner_ids = [1];
    Partner._onChanges = {
        turtles: function (obj) {
            const res = obj.turtles.map((command) => {
                if (command[0] === 1) {
                    // already an UPDATE command: do nothing
                    return command;
                }
                // convert LINK_TO commands to UPDATE commands
                const id = command[1];
                const record = Turtle._records.find((record) => record.id === id);
                return [1, id, pick(record, "turtle_int", "turtle_foo", "partner_ids")];
            });
            obj.turtles = res;
        },
    };
    onRpc((args) => {
        const ids = args.method === "web_read" ? " [" + args.args[0] + "]" : "";
        expect.step(args.method + ids);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top" limit="2" default_order="turtle_foo">
                        <field name="turtle_int"/>
                        <field name="turtle_foo" class="foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.foo")).toEqual(["blip", "kawa"]);

    // edit turtle_int field of first row
    await contains(".o_data_cell").click();
    await contains(".o_data_row .o_field_widget[name=turtle_int] input").edit(3, {
        confirm: false,
    });
    await contains(".o_form_view").click();
    expect(queryAllTexts(".o_data_cell.foo")).toEqual(["blip", "kawa"]);

    expect.verifySteps([
        "get_views",
        "web_read [1]", // main record
        "onchange",
        // this test's purpose is to assert that this rpc isn't
        // done, but yet it is. Actually, it wasn't before because mockOnChange
        // returned [1] as command list, instead of [[6, false, [1]]], so basically
        // this value was ignored. Now that mockOnChange properly works, the value
        // is taken into account but the basicmodel doesn't care it concerns a
        // record of the second page, and does the read. I don't think we
        // introduced a regression here, this test was simply wrong...
    ]);
});

test("one2many with several pages, onchange return command update on unknown record (readonly field)", async () => {
    Turtle._fields.turtle_int = fields.Integer({ readonly: true });
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [[1, 3, { turtle_int: 57, turtle_foo: "yop" }]];
        },
    };
    onRpc("web_save", ({ args }) => {
        expect(args[0]).toEqual([1]);
        // for unknownCommand, we should not send readonly fields
        expect(args[1]).toEqual({
            foo: "blip",
            turtles: [[1, 3, { turtle_foo: "yop" }]],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list editable="top" limit="1">
                        <field name="turtle_int"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name=foo] input").edit("blip", { confirm: false });
    await clickSave();
});

test("new record, with one2many with more default values than limit", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="2">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        context: { default_turtles: [1, 2, 3] },
    });
    expect(queryAllTexts(".o_data_row")).toEqual(["yop", "blip"]);

    await clickSave();
    expect(queryAllTexts(".o_data_row")).toEqual(["yop", "blip"]);
});

test("add a new line after limit is reached should behave nicely", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    Partner._onChanges = {
        turtles: function () {},
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="3" editable="bottom">
                        <field name="turtle_foo" required="1"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(4);

    await contains('div[name="turtle_foo"] .o_input').edit("a", { confirm: false });
    expect(".o_data_row").toHaveCount(4, {
        message: "should still have 4 data rows (the limit is increased to 4)",
    });
});

test.tags("desktop");
test("onchange in a one2many with non inline view on an existing record", async () => {
    Partner._fields.sequence = fields.Integer({ string: "Sequence", type: "integer" });
    Partner._records[0].sequence = 1;
    Partner._records[1].sequence = 2;
    Partner._onChanges = { sequence: function () {} };

    PartnerType._fields.partner_ids = fields.One2many({
        string: "Partner",
        relation: "partner",
    });
    PartnerType._records[0].partner_ids = [1, 2];
    Partner._views = {
        list: `
                <list>
                    <field name="sequence" widget="handle"/>
                    <field name="name"/>
                </list>`,
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner.type",
        arch: `
                <form>
                    <field name="partner_ids" widget="one2many"/>
                </form>`,
        resId: 12,
    });
    // swap 2 lines in the one2many
    await contains("tbody tr:eq(1) .o_handle_cell").dragAndDrop("tbody tr");

    expect.verifySteps(["get_views", "get_views", "web_read", "onchange", "onchange"]);
});

test.tags("desktop");
test("onchange in a one2many with non inline view on a new record", async () => {
    Turtle._onChanges = {
        name: function (obj) {
            if (obj.name) {
                obj.turtle_int = 44;
            }
        },
    };
    Turtle._views = {
        list: `
            <list editable="bottom">
                <field name="name"/>
                <field name="turtle_int"/>
            </list>`,
    };
    onRpc((args) => {
        expect.step(args.method || args.route);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" widget="one2many"/>
            </form>`,
    });

    // add a row and trigger the onchange
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('.o_data_row div[name="name"] input').edit("a name", { confirm: "blur" });

    expect(".o_field_cell[name=turtle_int]").toHaveText("44");

    expect.verifySteps([
        "get_views", // load main form
        "get_views", // load sub list
        "onchange", // main record
        "onchange", // sub record
        "onchange", // edition of name of sub record
    ]);
});

test.tags("desktop");
test('add a line, edit it and "Save & New"', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name" widget="char" class="do_not_remove_widget_char"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(0);
    // add a new record
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_widget input").edit("new record", { confirm: false });

    await contains(".modal .o_form_button_save").click();

    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(["new record"]);

    // reopen freshly added record and edit it
    await contains(".o_data_row .o_data_cell").click();
    await contains(".modal .o_field_widget input").edit("new record edited", { confirm: false });

    // save it, and choose to directly create another record
    await contains(".modal .modal-footer .btn-primary:eq(1)").click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_field_widget").toHaveText("");

    await contains(".modal .o_field_widget input").edit("another new record", { confirm: false });
    await contains(".modal .o_form_button_save").click();

    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual([
        "new record edited",
        "another new record",
    ]);
});

test.tags("desktop");
test('add a line with a context depending on the parent record, created a second record with "Save & New"', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="p" context="{'default_name': name}" >
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(0);
    expect(queryAllTexts("[name='p'] .o_data_row")).toEqual([]);
    await contains("[name='name'] input").edit("Jack", { confirm: "blur" });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal [name='name'] input").toHaveValue("Jack");

    await contains(".modal .o_form_button_save_new").click();
    expect(".modal [name='name'] input").toHaveValue("Jack");
    expect(queryAllTexts("[name='p'] .o_data_row")).toEqual(["Jack"]);

    await contains(".modal .o_form_button_save").click();
    expect(queryAllTexts("[name='p'] .o_data_row")).toEqual(["Jack", "Jack"]);
});

test("o2m add a line custom control create editable", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <control>
                            <create string="Add food" context="" />
                            <create string="Add pizza" context="{'default_name': 'pizza'}"/>
                        </control>
                        <control>
                            <create string="Add pasta" context="{'default_name': 'pasta'}"/>
                        </control>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    // new controls correctly added
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(queryAllTexts(".o_field_x2many_list_row_add a")).toEqual([
        "Add food",
        "Add pizza",
        "Add pasta",
    ]);

    // click add food
    // check it's empty
    await contains(".o_field_x2many_list_row_add a").click();
    expect(queryAllTexts(".o_data_cell")).toEqual([""]);

    // click add pizza
    // press enter to save the record
    // check it's pizza
    await contains(".o_field_x2many_list_row_add a:eq(1)").click();

    expect(
        '.o_field_widget[name="p"] .o_selected_row .o_field_widget[name="name"] input'
    ).toBeFocused();

    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_data_cell")).toEqual(["", "pizza", ""]);

    // click add pasta
    await contains(".o_field_x2many_list_row_add a:eq(2)").click();
    await clickSave();
    expect(queryAllTexts(".o_data_cell")).toEqual(["", "pizza", "", "pasta"]);
});

test("o2m add a line custom control create non-editable", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                    <control>
                        <create string="Add food" context="" />
                        <create string="Add pizza" context="{'default_name': 'pizza'}" />
                    </control>
                    <control>
                        <create string="Add pasta" context="{'default_name': 'pasta'}" />
                    </control>
                    <field name="name"/>
                </list>
                <form>
                    <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    // new controls correctly added
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(queryAllTexts(".o_field_x2many_list_row_add a")).toEqual([
        "Add food",
        "Add pizza",
        "Add pasta",
    ]);

    // click add food
    // check it's empty
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_form_button_save").click();
    expect(queryAllTexts(".o_data_cell")).toEqual([""]);

    // click add pizza
    // save the modal
    // check it's pizza
    await contains(".o_field_x2many_list_row_add a:eq(1)").click();
    await contains(".modal .o_form_button_save").click();
    expect(queryAllTexts(".o_data_cell")).toEqual(["", "pizza"]);

    // click add pasta
    // save the whole record
    // check it's pizzapasta
    await contains(".o_field_x2many_list_row_add a:eq(2)").click();
    await contains(".modal .o_form_button_save").click();
    expect(queryAllTexts(".o_data_cell")).toEqual(["", "pizza", "pasta"]);
});

test("o2m add an action button control", async () => {
    onRpc("do_something", (args) => {
        expect.step("do_something");
        expect(args.kwargs.context.parent_id).toBe(2);
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="p">
                    <list>
                        <control>
                            <create string="Create" context="{}" />
                            <button string="Action Button" name="do_something" class="btn-link" type="object" context="{'parent_id': parent.id}"/>
                        </control>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".o_field_x2many_list_row_add").toHaveText("CreateAction Button");

    await contains(".o_field_x2many_list_row_add button").click();
    expect.verifySteps(["do_something"]);
});

test("o2m button with parent in context", async () => {
    onRpc("test_button", (args) => {
        expect.step("test_button");
        expect(args.kwargs.context.parent_name).toBe("first record");
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="display_name"/>
                        <button string="Action Button" name="test_button" type="object" context="{'parent_name': parent.display_name}"/>
                    </list>
                </field>
            </form>`,
    });
    await contains('button[name="test_button"]').click();
    expect.verifySteps(["test_button"]);
});

test("o2m add a line custom control create align with handle", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="int_field" widget="handle"/>
                    </list>
                </field>
            </form>`,
    });

    // controls correctly added, at one column offset when handle is present
    expect(".o_list_table tr:eq(1) td").toHaveCount(2);
    expect(".o_list_table tr:eq(1) td:eq(0)").toHaveText("");
    expect(".o_list_table tr:eq(1) td:eq(1)").toHaveText("Add a line");
});

test.tags("desktop");
test("one2many form view with action button", async () => {
    // once the action button is clicked, the record is reloaded (via the
    // onClose handler, executed because the python method does not return
    // any action, or an ir.action.act_window_close) ; this test ensures that
    // it reloads the fields of the opened view (i.e. the form in this case).
    // See https://github.com/odoo/odoo/issues/24189
    mockService("action", {
        doActionButton(params) {
            Partner._records[1].name = "new name";
            Partner._records[1].timmy = [12];
            params.onClose();
        },
    });

    Partner._records[0].p = [2];
    PartnerType._views = {
        list: `
            <list>
                <field name="name"/>
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <button type="action" string="Set Timmy"/>
                        <field name="timmy"/>
                    </form>
                </field>
            </form>`,
    });
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("second record");

    // open one2many record in form view
    await contains(".o_data_cell").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view .o_data_row").toHaveCount(0);

    // click on the action button
    await contains(".modal .o_form_editable button").click();
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_data_cell").toHaveText("gold");

    // save the dialog
    await contains(".modal .modal-footer .btn-primary").click();

    expect(".o_data_cell").toHaveText("new name");
});

test.tags("desktop");
test("onchange affecting inline unopened list view", async () => {
    let numUserOnchange = 0;
    Users._onChanges = {
        partner_ids: function (obj) {
            numUserOnchange++;
        },
    };

    await mountView({
        type: "form",
        resModel: "res.users",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="partner_ids">
                            <form>
                                <field name="turtles">
                                    <list editable="bottom">
                                        <field name="name"/>
                                    </list>
                                </field>
                            </form>
                            <list>
                                <field name="name"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 17,
    });

    // add a turtle on second partner
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    await contains(".modal .o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_widget[name=name] input").edit("michelangelo", {
        confirm: false,
    });
    await contains(".modal .btn-primary").click();
    // open first partner so changes from previous action are applied
    await contains(".o_data_row .o_data_cell").click();
    await contains(".modal .btn-primary").click();
    await clickSave();

    expect(numUserOnchange).toBe(1, {
        message: "there should 1 and only 1 onchange from closing the partner modal",
    });

    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_data_row").toHaveCount(1, { message: "only 1 turtle for first partner" });
    expect(".modal .o_data_cell").toHaveText("donatello");
    await contains(".modal .modal-footer .btn-primary").click(); // Close

    await contains(".o_data_row:eq(1) .o_data_cell").click();
    expect(".modal .o_data_row").toHaveCount(1, { message: "only 1 turtle for second partner" });
    expect(".modal .o_data_cell").toHaveText("michelangelo");
    await contains(".modal .o_form_button_cancel").click();
});

test("click on URL should not open the record", async () => {
    Partner._records[0].turtles = [1];

    // avoid to open a new tab or the mail app
    const onClick = (ev) => {
        expect.step("link clicked");
        ev.preventDefault();
    };
    browser.addEventListener("click", onClick, { capture: true });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name" widget="email"/>
                        <field name="turtle_foo" widget="url"/>
                    </list>
                    <form/>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_email_cell a").click();
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["link clicked"]);

    await contains(".o_url_cell a").click();
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["link clicked"]);
});

test.tags("desktop");
test("create and edit on m2o in o2m, and press ESCAPE", async () => {
    Partner._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_trululu"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_selected_row").toHaveCount(1);

    await clickFieldDropdown("turtle_trululu");
    await contains("[name=turtle_trululu] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("turtle_trululu", "Create and edit...");

    expect(".modal .o_form_view").toHaveCount(1);

    await press("Escape");
    await animationFrame();

    expect(".modal .o_form_view").toHaveCount(0);
    expect(".o_selected_row").toHaveCount(1);
    expect(".o_selected_row [name=turtle_trululu] input").toBeFocused();
});

test.tags("desktop");
test("one2many add a line should not crash if orderedResIDs is not set on desktop", async () => {
    mockService("action", {
        doActionButton(args) {
            return Promise.reject();
        },
    });

    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <header>
                    <button name="post" type="object" string="Validate" class="oe_highlight"/>
                </header>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });

    await contains('button[name="post"]').click();
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row.o_selected_row").toHaveCount(1);
});

test.tags("mobile");
test("one2many add a line should not crash if orderedResIDs is not set on mobile", async () => {
    mockService("action", {
        doActionButton(args) {
            return Promise.reject();
        },
    });

    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <header>
                    <button name="post" type="object" string="Validate" class="oe_highlight"/>
                </header>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains('button[name="post"]').click();
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row.o_selected_row").toHaveCount(1);
});

test("one2many shortcut tab should not crash when there is no input widget", async () => {
    // create a one2many view which has no input (only 1 textarea in this case)
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo" widget="text"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // add a row, fill it, then trigger the tab shortcut
    await contains(".o_field_x2many_list_row_add a").click();
    // This is not how it should happen but non trusted event listeners are called sooner than
    // trusted ones so the update is called after the list's tab listener in which case the field is
    // not dirty when we press tab, therefore we need to set it dirty through onChange before pressing tab
    // so in practice we could only run the following line but it wont work since the tab keydown event is not trusted
    // await contains("[name=turtle_foo] textarea").edit("ninja", { confirm: false });
    await contains("[name=turtle_foo] textarea").edit("ninja", { confirm: "blur" });
    await contains("[name=turtle_foo]:eq(2)").click();

    expect("[name=turtle_foo] textarea").toBeFocused();
    await press("tab");
    await animationFrame();

    expect(queryAllTexts(".o_field_text")).toEqual(["blip", "ninja", ""]);
    expect(".o_field_text textarea").toHaveCount(1);
});

test("o2m add a line custom control create editable with 'tab'", async () => {
    onRpc("onchange", ({ kwargs }) => {
        expect.step("onchange");
        expect(kwargs.context.default_turtle_foo).toBe("soft");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="turtles">
                        <list editable="bottom">
                            <control>
                                <create string="Add soft shell turtle" context="{'default_turtle_foo': 'soft'}"/>
                            </control>
                            <field name="turtle_foo"/>
                            </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row .o_data_cell").click();
    // This is not how it should happen but non trusted event listeners are called sooner than
    // trusted ones so the update is called after the list's tab listener in which case the field is
    // not dirty when we press tab, therefore we need to set it dirty through onChange before pressing tab
    // so in practice we could only run the following line but it wont work since the tab keydown event is not trusted
    // await contains("[name=turtle_foo] textarea").edit("Test", { confirm: false });
    await contains("[name=turtle_foo] input").edit("Test", { confirm: "blur" });
    await contains("[name=turtle_foo]").click();
    expect(".o_data_row").toHaveCount(1);

    await press("Tab");
    await animationFrame();
    expect(".o_data_row").toHaveCount(2);
    expect.verifySteps(["onchange"]);
});

test("one2many with onchange, required field, shortcut enter", async () => {
    Turtle._onChanges = {
        turtle_foo: function () {},
    };

    let def;
    onRpc("onchange", () => def);
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo" required="1"/>
                    </list>
                </field>
            </form>`,
    });

    expect.verifySteps(["get_views", "onchange"]);

    // add a new line
    await contains(".o_field_x2many_list_row_add a").click();

    expect.verifySteps(["onchange"]);

    // we want to add a delay to simulate an onchange
    def = new Deferred();

    // write something in the field, edit will confirm with enter
    await contains("[name=turtle_foo] input").edit("hello");

    // check that nothing changed before the onchange finished
    expect("[name=turtle_foo] input").toHaveValue("hello");
    expect(".o_data_row").toHaveCount(1);

    expect.verifySteps(["onchange"]);

    // unlock onchange
    def.resolve();
    await animationFrame();

    // check the current line is added with the correct content and a new line is editable
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:eq(0) [name=turtle_foo]").toHaveText("hello");
    expect(".o_data_row:eq(1) [name=turtle_foo] input").toHaveValue("");

    expect.verifySteps(["onchange"]);
});

test("edit a field with a slow onchange in one2many", async () => {
    Turtle._onChanges = {
        turtle_foo: function () {},
    };

    let def;
    onRpc("onchange", () => def);
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });

    expect.verifySteps(["get_views", "onchange"]);

    // add a new line
    await contains(".o_field_x2many_list_row_add a").click();

    expect.verifySteps(["onchange"]);

    // we want to add a delay to simulate an onchange
    def = new Deferred();

    // write something in the field
    await contains("[name=turtle_foo] input").edit("hello", { confirm: false });
    expect("[name=turtle_foo] input").toHaveValue("hello");

    await contains(".o_form_view").click();

    // check that nothing changed before the onchange finished
    expect("[name=turtle_foo] input").toHaveValue("hello");

    expect.verifySteps(["onchange"]);

    // unlock onchange
    def.resolve();
    await animationFrame();

    // check the current line is added with the correct content
    expect(".o_data_row [name=turtle_foo]").toHaveText("hello");
});

test("no deadlock when leaving a one2many line with uncommitted changes", async () => {
    // Before unselecting a o2m line, field widgets are asked to commit their changes (new values
    // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
    // ensuring that we don't end up in a deadlock when a widget actually has some changes to
    // commit at that moment.
    onRpc((args) => {
        expect.step(args.method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".o_field_widget[name=turtles] input").edit("some foo value", {
        confirm: false,
    });

    // click to add a second row to unselect the current one, then save
    await contains(".o_field_x2many_list_row_add a").click();
    await clickSave();

    expect(".o_form_editable").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveText("some foo value");
    expect.verifySteps([
        "get_views", // main form view
        "onchange", // main record
        "onchange", // line 1
        "onchange", // line 2
        "web_save",
    ]);
});

test("one2many with extra field from server not in form", async () => {
    onRpc("web_save", (args) => {
        args.args[1].p[0][2].datetime = "2018-04-05 12:00:00";
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="datetime"/>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    // Add a record in the list
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal div[name=name] input").edit("michelangelo", { confirm: false });

    // Save the record in the modal (though it is still virtual)
    await contains(".modal .btn-primary").click();

    expect(".o_data_row").toHaveCount(1);
    let cells = queryAll(".o_data_cell");
    expect(cells[0]).toHaveText("");
    expect(cells[1]).toHaveText("michelangelo");

    // Save the whole thing
    await clickSave();

    // Redo asserts in RO mode after saving
    expect(".o_data_row").toHaveCount(1);
    cells = queryAll(".o_data_cell");
    expect(cells[0]).toHaveText("04/05/2018 13:00:00");
    expect(cells[1]).toHaveText("michelangelo");
});

test.tags("desktop");
test("one2many invisible depends on parent field", async () => {
    Partner._records[0].p = [2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="bar"/>
                            <field name="p">
                                <list>
                                    <field name="foo" column_invisible="parent.product_id"/>
                                    <field name="bar" column_invisible="not parent.bar"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect("th:not(.o_list_actions_header)").toHaveCount(2);

    await selectFieldDropdownItem("product_id", "xphone");

    expect("th:not(.o_list_actions_header)").toHaveCount(1, {
        message: "should be 1 column when the product_id is set",
    });
    await contains(".o_field_many2one[name=product_id] input").clear({ confirm: "blur" });
    expect("th:not(.o_list_actions_header)").toHaveCount(2, {
        message: "should be 2 columns in the one2many when product_id is not set",
    });
    await contains(".o_field_boolean[name=bar] input").click();
    expect("th:not(.o_list_actions_header)").toHaveCount(1, {
        message: "should be 1 column after the value change",
    });
});

test.tags("desktop");
test("column_invisible attrs on a button in a one2many list", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id"/>
                <field name="p">
                    <list>
                        <field name="foo"/>
                        <button name="abc" string="Do it" class="some_button" column_invisible="not parent.product_id"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_field_widget[name=product_id] input").toHaveValue("");
    expect(".o_list_table th").toHaveCount(2); // foo + trash bin
    expect(".some_button").toHaveCount(0);
    await selectFieldDropdownItem("product_id", "xphone");

    expect(".o_field_widget[name=product_id] input").toHaveValue("xphone");
    expect(".o_list_table th").toHaveCount(3); // foo + button + trash bin
    expect(".some_button").toHaveCount(1);
});

test.tags("desktop");
test("column_invisible attrs on adjacent buttons", async () => {
    Partner._records[0].p = [2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id"/>
                <field name="trululu"/>
                <field name="p">
                    <list>
                        <button name="abc1" string="Do it 1" class="some_button1"/>
                        <button name="abc2" string="Do it 2" class="some_button2" column_invisible="parent.product_id"/>
                        <field name="foo"/>
                        <button name="abc3" string="Do it 3" class="some_button3" column_invisible="parent.product_id"/>
                        <button name="abc4" string="Do it 4" class="some_button4" column_invisible="parent.trululu"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=product_id] input").toHaveValue("");
    expect(".o_field_widget[name=trululu] input").toHaveValue("aaa");
    expect(".o_list_table th").toHaveCount(4); // button group 1 + foo + button group 2 + trash bin
    expect(".some_button1").toHaveCount(1);
    expect(".some_button2").toHaveCount(1);
    expect(".some_button3").toHaveCount(1);
    expect(".some_button4").toHaveCount(0);

    await selectFieldDropdownItem("product_id", "xphone");

    expect(".o_field_widget[name=product_id] input").toHaveValue("xphone");
    expect(".o_field_widget[name=trululu] input").toHaveValue("aaa");
    expect(".o_list_table th").toHaveCount(3); // button group 1 + foo + trash bin
    expect(".some_button1").toHaveCount(1);
    expect(".some_button2").toHaveCount(0);
    expect(".some_button3").toHaveCount(0);
    expect(".some_button4").toHaveCount(0);
});

test("field context is correctly passed to x2m subviews", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" context="{'some_key': 1}">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <t t-if="context.some_key">
                                    <field name="turtle_foo"/>
                                </t>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span:contains('blip')").toHaveCount(1);
});

test.tags("desktop");
test("one2many kanban with widget handle", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    onRpc("write", (args) => {
        expect(args.args[1]).toEqual({
            turtles: [
                [1, 2, { turtle_int: 0 }],
                [1, 3, { turtle_int: 1 }],
                [1, 1, { turtle_int: 2 }],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <kanban>
                        <field name="turtle_int" widget="handle"/>
                        <templates>
                            <t t-name="card">
                                <field name="turtle_foo"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["yop", "blip", "kawa"]);

    // // should not work (form in mode "readonly")
    // await contains(".o_kanban_record:eq(0)").dragAndDrop(".o_kanban_record:eq(2)");
    // expect(
    //     queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(
    //     ["yop", "blip", "kawa"]
    // );

    await contains(".o_kanban_record:eq(0)").dragAndDrop(".o_kanban_record:eq(2)");

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["blip", "kawa", "yop"]);

    await clickSave();
});

test("one2many editable list: edit and click on add a line", async () => {
    Turtle._onChanges = {
        turtle_int: function () {},
    };
    onRpc("onchange", (args) => {
        expect.step("onchange");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom"><field name="turtle_int"/></list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(1);

    // edit first row
    await contains(".o_data_row .o_data_cell").click();
    expect(".o_data_row").toHaveClass("o_selected_row");
    await contains(".o_selected_row .o_field_widget[name=turtle_int] input").edit("44", {
        confirm: false,
    });
    expect.verifySteps([]);
    await contains(".o_field_x2many_list_row_add a").click();
    expect.verifySteps(["onchange", "onchange"]);

    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_cell:eq(0)").toHaveText("44");
    expect(".o_data_row:eq(1)").toHaveClass("o_selected_row");
});

test("many2manys inside a one2many are fetched in batch after onchange", async () => {
    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [
                [4, 1],
                [4, 2],
                [
                    1,
                    1,
                    {
                        turtle_foo: "leonardo",
                        partner_ids: [[4, 2]],
                    },
                ],
            ];
        },
    };
    onRpc((args) => {
        expect.step(args.method || args.route);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts('.o_field_widget[name="partner_ids"]')).toEqual([
        "second record",
        "second record\naaa",
    ]);

    expect.verifySteps(["get_views", "onchange"]);
});

test("two one2many fields with same relation and _onChanges", async () => {
    // this test simulates the presence of two one2many fields with _onChanges, such that
    // changes to the first o2m are repercuted on the second one
    Partner._fields.turtles2 = fields.One2many({
        string: "Turtles 2",
        type: "one2many",
        relation: "turtle",
        relation_field: "turtle_trululu",
    });
    Partner._onChanges = {
        turtles: function (obj) {
            // replicate changes on turtles2
            if (obj.turtles.length) {
                const command = obj.turtles2 && obj.turtles2[0];
                if (command) {
                    // second onchange (with ABC): there's already a create command
                    obj.turtles2 = [[1, command[1], obj.turtles[0][2]]];
                } else {
                    // first onchange (when adding the row): replicate the create command
                    obj.turtles2 = [[0, false, obj.turtles[0][2]]];
                }
            }
        },
        turtles2: () => {}, // simulate an onchange on turtles2 as well
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom"><field name="name" required="1"/></list>
                </field>
                <field name="turtles2">
                    <list editable="bottom"><field name="name" required="1"/></list>
                </field>
            </form>`,
    });

    // trigger first onchange by adding a line in turtles field (should add a line in turtles2)
    await contains('.o_field_widget[name="turtles"] .o_field_x2many_list_row_add a').click();
    await contains('.o_field_widget[name="turtles"] .o_field_widget[name="name"] input').edit(
        "ABC",
        { confirm: "blur" }
    );

    expect('.o_field_widget[name="turtles"] .o_data_row').toHaveCount(1, {
        message: "line of first o2m should have been created",
    });
    expect('.o_field_widget[name="turtles2"] .o_data_row').toHaveCount(1, {
        message: "line of second o2m should have been created",
    });

    // add a line in turtles2
    await contains('.o_field_widget[name="turtles2"] .o_field_x2many_list_row_add a').click();
    await contains('.o_field_widget[name="turtles2"] .o_field_widget[name="name"] input').edit(
        "DEF",
        { confirm: false }
    );

    expect('.o_field_widget[name="turtles"] .o_data_row').toHaveCount(1, {
        message: "we should still have 1 line in turtles",
    });
    expect('.o_field_widget[name="turtles2"] .o_data_row').toHaveCount(2);
    expect('.o_field_widget[name="turtles2"] .o_data_row:eq(1)').toHaveClass("o_selected_row");

    await clickSave();

    expect(queryAllTexts('.o_field_widget[name="turtles2"] .o_data_row')).toEqual(["ABC", "DEF"]);
});

test.tags("desktop");
test("one2many reset by onchange (of another field) while being edited", async () => {
    // In this test, we have a many2one and a one2many. The many2one has an onchange that
    // updates the value of the one2many. We set a new value to the many2one (name_create)
    // such that the onchange is delayed. During the name_create, we click to add a new row
    // to the one2many. After a while, we unlock the name_create, which triggers the onchange
    // and resets the one2many. At the end, we want the row to be in edition.

    const def = new Deferred();
    Partner._onChanges = {
        trululu: () => {},
    };
    onRpc("name_create", () => def);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="trululu"/>
                    <field name="p">
                        <list editable="top"><field name="product_id" required="1"/></list>
                    </field>
                </form>`,
    });

    // set a new value for trululu (will delay the onchange)
    await contains(".o_field_widget[name=trululu] input").edit("new value", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("trululu", `Create "new value"`);

    // add a row in p
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(0);

    // resolve the name_create to trigger the onchange, and the reset of p
    def.resolve();
    await animationFrame();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveClass("o_selected_row");
});

test("one2many with many2many_tags in list and list in form with a limit", async () => {
    // This test encodes a limitation of the current model architecture:
    // we have an nested x2manys, and the inner one is displayed as tags
    // in the list, and as a list in the form. As both the list and the
    // form will use the same Record datapoint, the config of their static
    // list will be the same. We obviously don't want to see the limit
    // applied on the tags (in the background) when opening the form. So
    // the stategy is to keep the initial config, and to ignore the
    // limit set on the list
    Partner._records[0].p = [1];
    Partner._records[0].turtles = [1, 2, 3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p">
                    <list>
                        <field name="turtles" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="turtles">
                            <list limit="2">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=p] .o_data_row").toHaveCount(1);
    expect(".o_data_row .o_field_many2many_tags .badge").toHaveCount(3);

    await contains(".o_data_cell").click();

    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_field_widget[name=turtles] .o_data_row").toHaveCount(3);
    expect(".modal .o_field_x2many_list .o_pager").not.toBeVisible();
});

test("one2many with many2many_tags in list and list in form, and onchange", async () => {
    Partner._onChanges = {
        bar: function (obj) {
            obj.p = [[0, 0, { turtles: [[0, 0, { name: "new turtle" }]] }]];
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p">
                    <list>
                        <field name="turtles" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="turtles">
                            <list editable="bottom">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_field_widget[name=p] .o_data_row").toHaveCount(1);
    expect(".o_data_row .o_field_many2many_tags .badge").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();

    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect(queryAllTexts(".modal .o_data_cell")).toEqual(["new turtle"]);

    await contains(".modal .o_field_x2many_list_row_add a").click();
    expect(".modal .o_field_widget[name=turtles] .o_data_row").toHaveCount(2);
    expect(queryAllTexts(".modal .o_data_cell")).toEqual(["new turtle", ""]);
    expect(".modal .o_field_widget[name=turtles] .o_data_row:eq(1)").toHaveClass("o_selected_row");
});

test("one2many with many2many_tags in list and list in form, and onchange (2)", async () => {
    Partner._onChanges = {
        bar: function (obj) {
            obj.p = [
                [
                    0,
                    0,
                    {
                        turtles: [
                            [
                                0,
                                0,
                                {
                                    display_name: "new turtle",
                                },
                            ],
                        ],
                    },
                ],
            ];
        },
    };
    Turtle._onChanges = {
        turtle_foo: function (obj) {
            obj.display_name = obj.turtle_foo;
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p">
                    <list>
                        <field name="turtles" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="turtles">
                            <list editable="bottom">
                                <field name="turtle_foo" required="1"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_field_widget[name=p] .o_data_row").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();

    expect(".modal .o_form_view").toHaveCount(1);

    await contains(".modal .o_field_x2many_list_row_add a").click();
    expect(".modal .o_field_widget[name=turtles] .o_data_row").toHaveCount(2);

    await contains(".modal .o_selected_row input").edit("another one", { confirm: false });
    await contains(".modal .modal-footer .btn-primary").click();

    expect(".modal").toHaveCount(0);

    expect(".o_field_widget[name=p] .o_data_row").toHaveCount(1);
    expect(".o_data_row .o_field_many2many_tags .badge").toHaveCount(2);
    expect(queryAllTexts(".o_data_row .o_field_many2many_tags .o_tag_badge_text")).toEqual([
        "new turtle",
        "another one",
    ]);
});

test("reorder one2many with many2many_tags in list and list in form", async () => {
    expect.assertions(3);

    Partner._records[0].p = [2, 4];
    Partner._records[0].p = [1, 4];

    Partner._views = {
        form: `
            <form>
                <field name="p">
                    <list editable="top">
                        <field name="int_field" widget="handle"/>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                        <field name="p" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click();
    expect(".modal").toHaveCount(1);
    expect(queryAllTexts(".modal [name='name']")).toEqual(["aaa", "first record"]);

    await contains(".modal tr:eq(2) .o_handle_cell").dragAndDrop(".modal tr:eq(1)");
    expect(queryAllTexts(".modal [name='name']")).toEqual(["first record", "aaa"]);
});

test("nested one2many, onchange, no command value", async () => {
    // This test ensures that we always send all values to onchange rpcs for nested
    // one2manys, even if some field hasn't changed. In this particular test case,
    // a first onchange returns a value for the inner one2many, and a second onchange
    // removes it, thus restoring the field to its initial empty value. From this point,
    // the nested one2many value must still be sent to onchange rpcs (on the main record),
    // as it might be used to compute other fields (so the fact that the nested o2m is empty
    // must be explicit).
    expect.assertions(1);

    Turtle._fields.o2m = fields.One2many({
        string: "o2m",
        relation: "partner",
        relation_field: "trululu",
    });
    Partner._onChanges.turtles = function (obj) {};
    Turtle._onChanges.turtle_bar = function (obj) {};

    let step = 1;
    onRpc((args) => {
        if (step === 3 && args.method === "onchange" && args.model === "partner") {
            expect(args.args[1].turtles[0][2]).toEqual({
                o2m: [],
                turtle_bar: false,
            });
        }
        if (args.model === "turtle") {
            if (step === 2) {
                return {
                    value: {
                        o2m: [[0, false, { name: "default" }]],
                        turtle_bar: true,
                    },
                };
            }
            if (step === 3) {
                const virtualId = args.args[1].o2m[0][1];
                return {
                    value: { o2m: [[2, virtualId]] },
                };
            }
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="o2m"/>
                        <field name="turtle_bar"/>
                    </list>
                </field>
            </form>`,
    });

    step = 2;
    await contains(".o_field_x2many_list_row_add a").click();
    step = 3;
    await contains(".o_data_row .o_field_boolean input").click();
});

test("edition in list containing widget with decoration", async () => {
    // We use here a badge widget and check its decoration is properly managed
    // in this scenario (we need a widget with specific decoration handling)
    Partner._records[0].p = [1, 2];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="int_field"/>
                        <field name="color" widget="badge" decoration-warning="int_field == 9"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:eq(1) .o_field_badge .badge").toHaveClass("text-bg-warning");

    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_selected_row .o_field_integer input").edit("44", { confirm: false });

    expect(".o_data_row:eq(1) .o_field_badge .badge").toHaveClass("text-bg-warning");
});

test("reordering embedded one2many with handle widget starting with same sequence", async () => {
    Turtle._records = [
        { id: 1, turtle_int: 1 },
        { id: 2, turtle_int: 1 },
        { id: 3, turtle_int: 1 },
        { id: 4, turtle_int: 2 },
        { id: 5, turtle_int: 3 },
        { id: 6, turtle_int: 4 },
    ];
    Partner._records[0].turtles = [1, 2, 3, 4, 5, 6];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_int" widget="handle"/>
                        <field name="id"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell:not(.o_handle_cell)")).toEqual([
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    ]);

    // Drag and drop the fourth line in first position
    await contains("tbody tr:eq(3) .o_handle_cell").dragAndDrop("tbody tr");

    expect(queryAllTexts(".o_data_cell:not(.o_handle_cell)")).toEqual([
        "4",
        "1",
        "2",
        "3",
        "5",
        "6",
    ]);

    await clickSave();
    expect(
        Turtle._records.map((r) => {
            return { id: r.id, turtle_int: r.turtle_int };
        })
    ).toEqual([
        { id: 1, turtle_int: 2 },
        { id: 2, turtle_int: 3 },
        { id: 3, turtle_int: 4 },
        { id: 4, turtle_int: 1 },
        { id: 5, turtle_int: 5 },
        { id: 6, turtle_int: 6 },
    ]);
});

test("combine contexts on o2m field and create tags", async () => {
    expect.assertions(1);
    onRpc("turtle", "onchange", (args) => {
        expect(args.kwargs.context).toEqual(
            {
                allowed_company_ids: [1],
                default_turtle_foo: "soft",
                default_turtle_bar: true,
                default_turtle_int: 2,
                lang: "en",
                tz: "taht",
                uid: 7,
            },
            {
                message:
                    "combined context should have the default_turtle_foo value from the <create>",
            }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles" context="{'default_turtle_foo': 'hard', 'default_turtle_bar': True}">
                        <list editable="bottom">
                            <control>
                                <create name="add_soft_shell_turtle" string="Add soft shell turtle" context="{'default_turtle_foo': 'soft', 'default_turtle_int': 2}"/>
                            </control>
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
});

test("do not call read if name already known", async () => {
    Partner._fields.product_id = fields.Many2one({ relation: "product", default: 37 });
    Partner._onChanges = {
        trululu: function (obj) {
            obj.trululu = 1;
        },
    };
    onRpc((args) => {
        expect.step(args.method + " on " + args.model);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu"/>
                <field name="product_id"/>
            </form>`,
    });

    expect(".o_field_widget[name=trululu] input").toHaveValue("first record");
    expect(".o_field_widget[name=product_id] input").toHaveValue("xphone");
    expect.verifySteps(["get_views on partner", "onchange on partner"]);
});

test("x2many default_order multiple fields", async () => {
    Partner._records = [
        { int_field: 10, id: 1, name: "record1" },
        { int_field: 12, id: 2, name: "record2" },
        { int_field: 11, id: 3, name: "record3" },
        { int_field: 12, id: 4, name: "record4" },
        { int_field: 10, id: 5, name: "record5" },
        { int_field: 10, id: 6, name: "record6" },
        { int_field: 11, id: 7, name: "record7" },
    ];

    Partner._records[0].p = [1, 7, 4, 5, 2, 6, 3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" >
                    <list default_order="int_field,id">
                        <field name="id"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_field_x2many_list .o_data_row .o_data_cell[name=id]")).toEqual([
        "1",
        "5",
        "6",
        "3",
        "7",
        "2",
        "4",
    ]);
});

test("x2many default_order multiple fields with limit", async () => {
    Partner._records = [
        { int_field: 10, id: 1, name: "record1" },
        { int_field: 12, id: 2, name: "record2" },
        { int_field: 11, id: 3, name: "record3" },
        { int_field: 12, id: 4, name: "record4" },
        { int_field: 10, id: 5, name: "record5" },
        { int_field: 10, id: 6, name: "record6" },
        { int_field: 11, id: 7, name: "record7" },
    ];

    Partner._records[0].p = [1, 7, 4, 5, 2, 6, 3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" >
                    <list default_order="int_field,id" limit="4">
                        <field name="id"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_field_x2many_list .o_data_row .o_data_cell[name=id]")).toEqual([
        "1",
        "5",
        "6",
        "3",
    ]);
});

test("one2many from a model that has been sorted", async () => {
    Partner._views = {
        list: `<list><field name="int_field"/></list>`,
        search: `<search/>`,
        form: `
            <form>
                <field name="turtles">
                    <list><field name="turtle_foo"/></list>
                </field>
            </form>`,
    };
    Partner._records[0].turtles = [3, 2];

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        name: "test",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });
    expect(".o_list_view").toHaveCount(1);
    expect(queryAllTexts(".o_data_cell")).toEqual(["10", "9", "0"]);

    await contains("th.o_column_sortable").click();
    expect(queryAllTexts(".o_data_cell")).toEqual(["0", "9", "10"]);

    await contains(".o_data_row:eq(2) .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".o_data_cell")).toEqual(["kawa", "blip"], {
        message: "The o2m should not have been sorted.",
    });
});

test("prevent the dialog in readonly x2many list view with option no_open True", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="bottom" no_open="True">
                            <field name="turtle_foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect('.o_data_row:contains("blip")').toHaveCount(1, {
        message: "There should be one record in x2many list view",
    });
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal").toHaveCount(0, {
        message: "There is should be no dialog open on click of readonly list row",
    });
});

test("delete a record while adding another one in a multipage", async () => {
    // in a one2many with at least 2 pages, add a new line. Delete the line above it.
    // it should load the next line to display it on the page.
    Partner._records[0].turtles = [2, 3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="turtles">
                            <list editable="bottom" limit="1" decoration-muted="turtle_bar == False">
                                <field name="turtle_foo"/>
                                <field name="turtle_bar"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    // add a line (virtual record)
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=turtle_foo] input").edit("pi", { confirm: false });
    // delete the line above it
    await contains(".o_list_record_remove").click();
    // the next line should be displayed below the newly added one
    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_cell")).toEqual(["pi", "", "kawa", ""], {
        message: "should display the correct records on page 1",
    });
});

test("one2many, onchange, edition and multipage...", async () => {
    Partner._onChanges = {
        turtles: function (obj) {
            obj.turtles = [[5]].concat(obj.turtles);
        },
    };

    Partner._records[0].turtles = [1, 2, 3];
    onRpc((args) => {
        expect.step(args.method + " " + args.model);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom" limit="2">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=turtle_foo] input").edit("nora", { confirm: false });
    await contains(".o_field_x2many_list_row_add a").click();

    expect.verifySteps([
        "get_views partner",
        "web_read partner",
        "onchange turtle",
        "onchange partner",
        "onchange partner",
        "onchange turtle",
        "onchange partner",
    ]);
});

test("x2many multipage, onchange returning update commands with readonly field", async () => {
    expect.assertions(3);

    Partner._records[0].turtles = [1, 2];
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [
                [1, 1, { name: "rec 1", turtle_foo: "new val 1" }],
                [1, 2, { name: "rec 2", turtle_foo: "new val 2" }],
            ];
        },
    };
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            foo: "trigger onchange",
            turtles: [
                [1, 1, { name: "rec 1" }],
                [1, 2, { name: "rec 2" }],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list limit="1">
                        <field name="name"/>
                        <field name="turtle_foo" readonly="1"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["leonardo", "yop"]);

    await contains(".o_field_widget[name=foo] input").edit("trigger onchange", { confirm: "blur" });
    expect(queryAllTexts(".o_data_cell")).toEqual(["rec 1", "new val 1"]);

    await clickSave();
});

test("x2many multipage, onchange returning update commands with readonly field (2)", async () => {
    expect.assertions(3);

    Partner._records[0].turtles = [1, 2];
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [
                [1, 1, { name: "rec 1", turtle_foo: "new val 1" }],
                [1, 2, { name: "rec 2", turtle_foo: "new val 2" }],
            ];
        },
    };
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            foo: "trigger onchange",
            turtles: [
                [1, 1, { name: "rec 1" }],
                [1, 2, { name: "rec 2" }],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list limit="1">
                        <field name="name" readonly="not context.get('some_key')"/>
                        <field name="turtle_foo" readonly="context.get('some_key')"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        context: { some_key: true },
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["leonardo", "yop"]);

    await contains(".o_field_widget[name=foo] input").edit("trigger onchange", { confirm: "blur" });
    expect(queryAllTexts(".o_data_cell")).toEqual(["rec 1", "new val 1"]);

    await clickSave();
});

test("x2many multipage, onchange returning update commands with readonly field (3)", async () => {
    expect.assertions(3);

    Partner._records[0].turtles = [1, 2];
    Partner._onChanges = {
        foo: function (obj) {
            obj.turtles = [
                [1, 1, { name: "rec 1", turtle_foo: "new val 1" }],
                [1, 2, { name: "rec 2", turtle_foo: "new val 2" }],
            ];
        },
    };
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            foo: "trigger onchange",
            turtles: [
                [1, 1, { name: "rec 1" }],
                // we can't evaluate the readonly expressions for the record of
                // second page, so we send both fields
                [1, 2, { name: "rec 2", turtle_foo: "new val 2" }],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles">
                    <list limit="1">
                        <field name="name" readonly="not turtle_bar"/>
                        <field name="turtle_foo" readonly="turtle_bar"/>
                        <field name="turtle_bar" column_invisible="1"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
        context: { some_key: true },
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["leonardo", "yop"]);

    await contains(".o_field_widget[name=foo] input").edit("trigger onchange", { confirm: "blur" });
    expect(queryAllTexts(".o_data_cell")).toEqual(["rec 1", "new val 1"]);

    await clickSave();
});

test("onchange on unloaded record clearing posterious change", async () => {
    let numUserOnchange = 0;
    Users._onChanges = {
        partner_ids: function (obj) {
            numUserOnchange++;
        },
    };

    await mountView({
        type: "form",
        resModel: "res.users",
        arch: `
            <form>
                <field name="partner_ids">
                    <form>
                        <field name="trululu"/>
                        <field name="turtles">
                            <list editable="bottom">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 17,
    });

    // open first partner and change turtle name
    await contains(".o_data_row .o_data_cell").click();
    await contains(".modal .o_data_row .o_data_cell").click();
    await contains(".modal .o_field_widget[name=name] input").edit("Donatello", { confirm: false });
    await contains(".modal .btn-primary").click();

    await contains(".o_data_row:eq(1) .o_data_cell").click();
    await contains(".modal .o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_widget[name=name] input").edit("Michelangelo", {
        confirm: false,
    });
    await contains(".modal .btn-primary").click();

    expect(numUserOnchange).toBe(2, {
        message: "there should be 2 and only 2 onchange from closing the partner modal",
    });

    // check first record still has change
    await contains(".o_data_row .o_data_cell").click();
    expect(".modal .o_data_row").toHaveCount(1, { message: "only 1 turtle for first partner" });
    expect(".modal .o_data_cell").toHaveText("Donatello");
    await contains(".modal .o_form_button_cancel").click();

    // check second record still has changes
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    expect(".modal .o_data_row").toHaveCount(1, { message: "only 1 turtle for second partner" });
    expect(".modal .o_data_cell").toHaveText("Michelangelo");
    await contains(".modal .o_form_button_cancel").click();

    // re-open, edit michelangelo row, click out -> row still there, in readonly
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    await contains(".modal .o_data_row .o_data_cell").click();
    expect(".modal .o_selected_row").toHaveCount(1);
    await contains(".modal").click();
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_data_cell").toHaveText("Michelangelo");
});

test("quickly switch between pages in one2many list", async () => {
    Partner._records[0].turtles = [1, 2, 3];

    const readDefs = [null, new Deferred(), null];
    onRpc("web_read", async (args) => {
        const recordID = args.args[0][0];
        await readDefs[recordID - 1];
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list limit="1">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_data_cell").toHaveText("leonardo");

    await contains(".o_field_widget[name=turtles] .o_pager_next").click();
    expect(".o_field_widget[name=turtles] .o_pager_next").not.toBeEnabled();

    readDefs[1].resolve();
    await animationFrame();
    expect(".o_data_cell").toHaveText("donatello");

    await contains(".o_field_widget[name=turtles] .o_pager_next").click();
    expect(" .o_data_cell").toHaveText("raphael");
});

test("one2many column visiblity depends on onchange of parent field", async () => {
    Partner._records[0].p = [2];
    Partner._records[0].bar = false;

    let triggerOnchange = false;
    Partner._onChanges.p = function (obj) {
        if (triggerOnchange) {
            obj.bar = true;
        }
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="p">
                    <list editable="bottom">
                        <field name="foo"/>
                        <field name="int_field" column_invisible="not parent.bar"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // bar is false so there should be 1 column
    expect(".o_list_renderer th:not(.o_list_actions_header)").toHaveCount(1);
    expect(".o_list_renderer .o_data_row").toHaveCount(1);

    // add a new o2m record
    await contains(".o_field_x2many_list_row_add a").click();
    triggerOnchange = true;
    await contains(".o_field_one2many input").edit("New line", { confirm: false });
    await contains(".o_form_view").click();

    expect(".o_list_renderer th:not(.o_list_actions_header)").toHaveCount(2);
});

test.tags("desktop");
test("one2many column_invisible on view not inline", async () => {
    Partner._records[0].p = [2];
    Partner._views = {
        list: `
            <list>
                <field name="foo" column_invisible="parent.product_id"/>
                <field name="bar" column_invisible="not parent.bar"/>
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="bar"/>
                            <field name="p" widget="one2many"/>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect("th:not(.o_list_actions_header)").toHaveCount(2);
    await selectFieldDropdownItem("product_id", "xphone");
    expect("th:not(.o_list_actions_header)").toHaveCount(1, {
        message: "should be 1 column when the product_id is set",
    });
    await contains(".o_field_many2one[name=product_id] input").clear({ confirm: "blur" });
    expect("th:not(.o_list_actions_header)").toHaveCount(2, {
        message: "should be 2 columns in the one2many when product_id is not set",
    });
    await contains(".o_field_boolean[name=bar] input").click();
    expect("th:not(.o_list_actions_header)").toHaveCount(1, {
        message: "should be 1 column after the value change",
    });
});

test.tags("desktop");
test("one2many field in edit mode with optional fields and trash icon", async () => {
    Partner._records[0].p = [2];
    Partner._views = {
        list: `
                <list editable="top">
                    <field name="foo" optional="show"/>
                    <field name="bar" optional="hide"/>
                </list>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="p"/></form>`,
        resId: 1,
    });

    expect(".o_field_one2many table .o_optional_columns_dropdown .dropdown-toggle").toHaveCount(1);

    // should have 2 columns 1 for foo and 1 for trash icon, dropdown is displayed
    // on trash icon cell, no separate cell created for trash icon and advanced field dropdown
    expect(".o_field_one2many th").toHaveCount(2, {
        message: "should be 2 th in the one2many edit mode",
    });
    expect(".o_field_one2many .o_data_row:first > td").toHaveCount(2, {
        message: "should be 2 cells in the one2many in edit mode",
    });

    await contains(".o_optional_columns_dropdown .dropdown-toggle").click();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(2, {
        message: "dropdown have 2 advanced field foo with checked and bar with unchecked",
    });
    await contains(".o-dropdown--menu .dropdown-item:eq(1)").click();
    expect(".o_field_one2many th").toHaveCount(3, {
        message: "should be 3 th in the one2many after enabling bar column from advanced dropdown",
    });

    await contains(".o-dropdown--menu .dropdown-item").click();
    expect(".o_field_one2many th").toHaveCount(2, {
        message: "should be 2 th in the one2many after disabling foo column from advanced dropdown",
    });
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(2, {
        message: "dropdown is still open",
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o-dropdown--menu").toHaveCount(0, { message: "dropdown is closed" });
    expect(".o_field_one2many tr.o_selected_row").toHaveCount(1);

    await contains(".o_optional_columns_dropdown .dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item").click();
    expect(".o_field_one2many tr.o_selected_row").toHaveCount(1);
    expect(".o_field_one2many th").toHaveCount(3, {
        message:
            "should be 3 th in the one2many after re-enabling foo column from advanced dropdown",
    });

    // optional columns must be preserved after save
    await clickSave();
    expect(".o_field_one2many th").toHaveCount(3, {
        message: "should have 3 th in the one2many after reloading whole form view",
    });
});

test("x2many list sorted by many2one", async () => {
    Partner._records[0].p = [1, 2, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="id"/>
                        <field name="trululu"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts(".o_data_row .o_list_number")).toEqual(["1", "2", "4"], {
        message: "should have correct order initially",
    });

    await contains(".o_list_renderer thead th:eq(1)").click();

    expect(queryAllTexts(".o_data_row .o_list_number")).toEqual(["4", "1", "2"], {
        message: "should have correct order (ASC)",
    });

    await contains(".o_list_renderer thead th:eq(1)").click();

    expect(queryAllTexts(".o_data_row .o_list_number")).toEqual(["2", "1", "4"], {
        message: "should have correct order (DESC)",
    });
});

test("one2many with extra field from server not in (inline) form", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="datetime"/>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    // Add a record in the list
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=name] input").edit("michelangelo", { confirm: false });

    // Save the record in the modal (though it is still virtual)
    await contains(".modal .modal-footer .btn-primary").click();
    expect(".o_data_row").toHaveCount(1);
});

test("one2many with extra X2many field from server not in inline form", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="turtles"/>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
    });

    // Add a first record in the list
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_field_widget[name=name] input").edit("first", { confirm: false });

    // Save & New
    await contains(".modal .btn-primary:eq(1)").click();
    await contains(".modal .o_field_widget[name=name] input").edit("second", { confirm: false });

    // Save & Close
    await contains(".modal .btn-primary").click();

    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["first", "second"]);
});

test("when Navigating to a one2many with tabs, the button add a line receives the focus", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="qux"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="turtles">
                                <list editable="bottom">
                                    <field name="turtle_foo"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains("[name=qux] input").click();
    expect("[name=qux] input").toBeFocused();
    // next tabable element is notebook tab
    await press("Tab");
    // go inside one2many
    await press("Tab");
    await animationFrame();
    expect(".o_field_x2many_list_row_add a").toBeFocused();
});

test("Navigate to a one2many with tab then tab again focus the next field", async () => {
    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="qux"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="turtles">
                                <list editable="bottom">
                                    <field name="turtle_foo"/>
                                    <field name="turtle_description"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains("[name=qux] input").click();
    expect("[name=qux] input").toBeFocused();
    // next tabable element is notebook tab
    await press("Tab");
    // go inside one2many
    await press("Tab");
    await animationFrame();

    expect(".o_field_x2many_list_row_add a").toBeFocused();
    expect("[name=turtles] .o_selected_row").toHaveCount(0);
    // trigger Tab event and check that the default behavior can happen.
    expect(getNextFocusableElement()).toBe(queryOne("[name=foo] input"));
    await press("Tab");
    expect("[name=foo] input").toBeFocused();
});

test("when Navigating to a one2many with tabs, not filling any field and hitting tab, no line is added and the next field is focused", async () => {
    Partner._records[0].turtles = [];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="qux"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="turtles">
                                <list editable="bottom">
                                    <field name="turtle_foo"/>
                                    <field name="turtle_description"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains("[name=qux] input").click();
    expect("[name=qux] input").toBeFocused();
    // next tabable element is notebook tab
    await press("Tab");
    // go inside one2many
    await press("Tab");
    await animationFrame();

    expect(".o_field_x2many_list_row_add a").toBeFocused();
    expect("[name=turtles] .o_selected_row").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a").click();
    expect("[name=turtle_foo] input").toBeFocused();

    await press("Tab"); // go to turtle_description field
    await animationFrame();
    expect("[name=turtle_description] textarea").toBeFocused();

    expect(getNextFocusableElement()).toBe(queryOne("[name=foo] input"));
    // trigger Tab event and check that the default behavior can happen.
    await press("Tab");
    expect("[name=foo] input").toBeFocused();
});

test("when Navigating to a one2many with tabs, editing in a popup, the popup should receive the focus then give it back", async () => {
    Partner._records[0].turtles = [];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="qux"/>
                    </group>
                    <notebook>
                        <page string="Partner page">
                            <field name="turtles">
                                <list>
                                    <field name="turtle_foo"/>
                                    <field name="turtle_description"/>
                                </list>
                                <form>
                                    <group>
                                        <field name="turtle_foo"/>
                                        <field name="turtle_int"/>
                                    </group>
                                </form>
                            </field>
                        </page>
                    </notebook>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    await contains("[name=qux] input").click();
    expect("[name=qux] input").toBeFocused();
    // next tabable element is notebook tab
    await press("Tab");
    // go inside one2many
    await press("Tab");
    await animationFrame();
    expect(".o_field_x2many_list_row_add a").toBeFocused();

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal [name=turtle_foo] input").toBeFocused();

    await press("Escape");
    await animationFrame();

    expect(".modal").toHaveCount(0);
    expect(".o_field_x2many_list_row_add a").toBeFocused();
});

test.tags("desktop");
test("when creating a new many2one on a x2many then discarding it immediately with ESCAPE, it should not crash", async () => {
    Partner._records[0].turtles = [];
    Partner._views = {
        form: `
                <form>
                    <field name="foo"/>
                    <field name="bar"/>
                </form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="turtles">
                        <list editable="top">
                            <field name="turtle_foo"/>
                            <field name="turtle_trululu"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    // add a new line
    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_selected_row").toHaveCount(1);

    await clickFieldDropdown("turtle_trululu");
    await contains(".o_field_widget[name=turtle_trululu] input").edit("ABC", {
        confirm: false,
    });
    await runAllTimers();

    // Discard input value
    press("Escape").then(() => {
        // ... then discard record
        press("Escape");
    });
    clickFieldDropdownItem("turtle_trululu", "Create and edit..."); // Open create modal
    await animationFrame();
    await animationFrame();

    expect(".modal").toHaveCount(0);
    expect(".o_selected_row").toHaveCount(0);
});

test.tags("desktop");
test("navigating through an editable list with custom controls", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="name"/>
                    <field name="p">
                        <list editable="bottom">
                            <control>
                                <create string="Custom 1" context="{'default_foo': '1'}"/>
                                <create string="Custom 2" context="{'default_foo': '2'}"/>
                            </control>
                            <field name="foo"/>
                        </list>
                    </field>
                    <field name="int_field"/>
                </form>`,
    });

    expect("[name=name] input").toBeFocused();

    expect("[name=p] .o_selected_row").toHaveCount(0);

    // press tab to navigate to the list
    expect(getNextFocusableElement()).toBe(queryFirst(".o_field_x2many_list_row_add a"));
    await press("Tab");

    expect(".o_field_x2many_list_row_add a:eq(0)").toBeFocused();

    // press right to focus the second control
    await press("ArrowRight");
    await animationFrame();

    expect(".o_field_x2many_list_row_add a:eq(1)").toBeFocused();

    // press left to come back to first control
    await press("ArrowLeft");
    await animationFrame();

    expect(".o_field_x2many_list_row_add a:eq(0)").toBeFocused();
    expect(getNextFocusableElement()).toBe(queryOne(".o_field_x2many_list_row_add a:eq(1)"));
    await press("Tab");
    expect(".o_field_x2many_list_row_add a:eq(1)").toBeFocused();

    expect(getNextFocusableElement()).toBe(queryOne("[name=int_field] input"));
    await press("Tab");
    expect("[name=int_field] input").toBeFocused();
});

test("be able to press a key on the keyboard when focusing a column header without crashing", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="turtle_int" />
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_list_renderer .o_column_sortable").click();
    await press("a");
    await animationFrame();
    expect(".o_data_row").toHaveCount(1);
});

test("Navigate from an invalid but not dirty row", async () => {
    Partner._records[0].p = [2, 4];
    Partner._records[1].name = ""; // invalid record

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name" required="1" />
                        <field name="int_field" readonly="1" />
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click(); // edit the first row

    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");

    await press("Tab"); // navigate with "Tab" to the second row
    await animationFrame();

    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(1)").toHaveClass("o_selected_row");
    expect(".o_invalid_cell").toHaveCount(0);

    await contains(".o_data_cell").click(); // come back on first row

    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_invalid_cell").toHaveCount(0);

    await press("Enter"); // try to navigate with "Enter" to the second row
    await animationFrame();

    expect(".o_data_row.o_selected_row").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_invalid_cell").toHaveCount(1);
});

test.tags("desktop");
test("Check onchange with two consecutive one2one", async () => {
    Product._fields.product_partner_ids = fields.One2many({
        string: "User",
        relation: "partner",
    });
    Product._records[0].product_partner_ids = [1];
    Product._records[1].product_partner_ids = [2];
    Turtle._fields.product_ids = fields.One2many({
        string: "Product",
        relation: "product",
    });
    Turtle._fields.user_ids = fields.One2many({
        string: "Product",
        relation: "res.users",
    });
    Turtle._onChanges = {
        turtle_trululu: function (record) {
            record.product_ids = [[4, 37]];
            record.user_ids = [
                [4, 17],
                [4, 19],
            ];
        },
    };

    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form string="Turtles">
                <field string="Product" name="turtle_trululu"/>
                <field readonly="1" string="Related field" name="product_ids">
                    <list>
                        <field widget="many2many_tags" name="product_partner_ids"/>
                    </list>
                </field>
                <field readonly="1" string="Second related field" name="user_ids">
                    <list>
                        <field widget="many2many_tags" name="partner_ids"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await clickFieldDropdown("turtle_trululu");
    await press("Enter");
    await animationFrame();

    expect(
        queryAllTexts(
            '.o_field_many2many_tags[name="product_partner_ids"] .badge.o_tag_color_0 > .o_tag_badge_text'
        )
    ).toEqual(["first record"], {
        message: "should have the correct value in the many2many tag widget",
    });
    expect(
        queryAllTexts(
            '.o_field_many2many_tags[name="partner_ids"] .badge.o_tag_color_0 > .o_tag_badge_text'
        )
    ).toEqual(["first record", "second record"], {
        message: "should have the correct values in the many2many tag widget",
    });
});

test("does not crash when you parse a tree arch containing another tree arch", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="turtles">
                            <list>
                                <field name="turtle_foo"/>
                            </list>
                        </field>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_list_renderer").toHaveCount(1);
});
test("open a one2many record containing a one2many", async () => {
    Partner._views = {
        [["form", 1234]]: `
            <form>
                <field name="turtles" >
                    <list>
                        <field name="name" />
                    </list>
                </field>
            </form>`,
    };

    patchWithCleanup(browser.localStorage, {
        setItem(args) {
            expect.step(`localStorage setItem ${args}`);
        },
        getItem(args) {
            expect.step(`localStorage getItem ${args}`);
            return null;
        },
    });

    const rec = Partner._records.find(({ id }) => id === 2);
    rec.p = [1];
    await mountView({
        type: "form",
        arch: `<form>
            <field name="p" context="{ 'form_view_ref': 1234 }">
                <list><field name="name" /></list>
            </field>
        </form>`,
        resModel: "partner",
        resId: 2,
    });

    expect.verifySteps([
        "localStorage getItem pwaService.installationState",
        "localStorage getItem optional_fields,partner,form,123456789,p,list,name",
        "localStorage getItem debug_open_view,partner,form,123456789,p,list,name",
    ]);

    await contains(".o_data_cell").click();
    expect(".modal .o_data_row").toHaveCount(1);
    expect.verifySteps([
        "localStorage getItem optional_fields,partner,form,123456789,p,list,name",
        "localStorage getItem debug_open_view,partner,form,123456789,p,list,name",
        "localStorage getItem optional_fields,partner,form,123456789,turtles,list,name",
        "localStorage getItem debug_open_view,partner,form,123456789,turtles,list,name",
    ]);
});

test("open a one2many record with optional open record displayed", async () => {
    Partner._views = {
        [["form", false]]: `<form>
            <field name="p" context="{ 'form_view_ref': 1234 }">
                <list editable="bottom"><field name="name" /></list>
            </field>
        </form>`,
        [["form", 1234]]: `
            <form>
                <field name="name"/>
            </form>`,
        [["search", false]]: `<search/>`,
    };
    let firstLoad = true;

    patchWithCleanup(localStorage, {
        getItem(key) {
            const value = super.getItem(...arguments);
            if (key.startsWith("debug_open_view")) {
                expect.step(["getItem", key, value]);
            }
            return value;
        },
        setItem(key, value) {
            if (key.startsWith("debug_open_view")) {
                expect.step(["setItem", key, value]);
            }
            super.setItem(...arguments);
        },
    });
    onRpc("get_views", ({ model, method, kwargs }) => {
        if (firstLoad) {
            firstLoad = false;
        } else {
            expect(kwargs.context.form_view_ref).toBe(1234);
            expect.step(`${model}.${method}`);
        }
    });
    serverState.debug = "1";
    const rec = Partner._records.find(({ id }) => id === 2);
    rec.p = [1];

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        res_id: 2,
    });

    const localStorageKey = "debug_open_view,partner,form,false,p,list,name";
    expect.verifySteps([["getItem", localStorageKey, null]]);

    expect(`td.o_list_record_open_form_view`).toHaveCount(0);
    expect(".o_optional_columns_dropdown").toHaveCount(1);
    await contains(".o_optional_columns_dropdown button").click();
    expect(".o-dropdown-item:contains('View Button')").toHaveCount(1);
    await contains(".o-dropdown-item:contains('View Button')").click();
    expect.verifySteps([
        ["setItem", localStorageKey, true],
        ["getItem", localStorageKey, "true"],
    ]);

    expect(`td.o_list_record_open_form_view`).toHaveCount(1, {
        message: "button to open form view should be present on each rows",
    });

    await contains(`td.o_list_record_open_form_view`).click();
    expect.verifySteps(["partner.get_views"]);
});

test("if there are less than 4 lines in a one2many, empty lines must be displayed to cover the difference.", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // Should only contain the "Add a line" line and 3 blank lines
    expect(".o_list_renderer tbody tr .o_data_row").toHaveCount(0);
    expect(".o_list_renderer tbody tr .o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_renderer tbody tr td:eq(0)").toHaveClass("o_field_x2many_list_row_add");
    expect(".o_list_renderer tbody tr").toHaveCount(4);

    await contains(".o_field_x2many_list_row_add a").click();
    // Should only contain a new row, the "Add a line" line and 2 blank lines
    expect(".o_list_renderer tbody tr.o_data_row").toHaveCount(1);
    expect(".o_list_renderer tbody tr:eq(0)").toHaveClass("o_data_row");
    expect(".o_list_renderer tbody tr .o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_renderer tbody tr:eq(1) td").toHaveClass("o_field_x2many_list_row_add");
    expect(".o_list_renderer tbody tr").toHaveCount(4);
});

test("one2many can delete a new record", async () => {
    onRpc("web_save", (args) => {
        expect.step("web_save"); // should not happen
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="foo"/>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="foo" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(0);

    await contains(".o-kanban-button-new").click();
    await contains(".modal .o_form_button_save").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);

    await contains(".o_kanban_record:not(.o_kanban_ghost)").click();
    expect(".modal .o_btn_remove").toHaveCount(1);

    await contains(".modal .o_btn_remove").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(0);

    await clickSave();
    expect.verifySteps([]);
});

test("toggle boolean in o2m with the formView in edition", async () => {
    Partner._onChanges = {
        turtles: () => {},
    };
    Turtle._onChanges = {
        turtle_bar: () => {},
    };
    onRpc((args) => {
        expect.step(args.method + " " + args.model);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_bar" widget="boolean_toggle"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views partner", "web_read partner"]);

    await contains(".o_boolean_toggle").click();
    expect.verifySteps(["onchange partner"]);
});

test("Boolean toggle in x2many must not be editable if form is not editable", async () => {
    Turtle._views = {
        [["form", false]]: /* xml */ `
            <form>
                <field name="turtle_bar" widget="boolean_toggle"/>
                <field name="partner_ids">
                    <list>
                        <field name="bar" widget="boolean_toggle"/>
                    </list>
                </field>
            </form>
        `,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form edit="0">
                    <field name="turtles">
                        <list>
                            <field name="turtle_bar" widget="boolean_toggle"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    expect(".o_form_renderer").toHaveClass("o_form_readonly");
    const booleanToggle = queryOne(
        "[name='turtles'] .o_data_row [name='turtle_bar'] .o_boolean_toggle input"
    );
    expect(booleanToggle).not.toBeEnabled({
        message: "The boolean toggle should be disabled when the form is readonly",
    });

    await contains(".o_data_cell").click();
    expect(".modal-dialog").toHaveCount(1);
    expect(".o_form_renderer").toHaveClass("o_form_readonly");
    const booleanToggleInDialog = queryOne(".modal [name='turtle_bar'] input");
    expect(booleanToggleInDialog).not.toBeEnabled({
        message:
            "The boolean toggle in the form view dialog should be disabled when the main form is readonly",
    });
    expect(
        ".modal [name='partner_ids'] .o_data_row [name='bar'] .o_boolean_toggle input"
    ).not.toBeEnabled({
        message:
            "The boolean toggle in x2m in the form view dialog should be disabled when the main form is readonly",
    });
});

test("create a new record with an x2m invisible", async () => {
    onRpc("onchange", (args) => {
        expect(args.args[3]).toEqual({
            display_name: {},
            p: {
                fields: {
                    int_field: {},
                    trululu: {
                        fields: {
                            display_name: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
        });
        return {
            value: {
                p: [
                    [
                        0,
                        false,
                        {
                            int_field: 4,
                            trululu: { id: 1, name: "first record" },
                        },
                    ],
                ],
            },
        };
    });
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        const commands = args.args[1].p;
        expect(commands).toEqual([[0, commands[0][1], { int_field: 4, trululu: 1 }]]);
        expect(args.kwargs.specification).toEqual({
            display_name: {},
            p: {},
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" invisible="1">
                    <list>
                        <field name="int_field"/>
                        <field name="trululu"/>
                    </list>
                </field>
            </form>`,
    });

    expect("[name='p']").toHaveCount(0);
    expect.verifySteps(["get_views", "onchange"]);

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("edit a record with an x2m invisible", async () => {
    onRpc((args) => {
        expect.step(`${args.method} ${args.model}`);
    });
    onRpc("web_read", (args) => {
        expect(args.kwargs.specification).toEqual({
            display_name: {},
            foo: {},
            turtles: {},
        });
    });
    onRpc("web_save", (args) => {
        expect(args.args[1]).toEqual({
            foo: "plop",
        });
        expect(args.kwargs.specification).toEqual({
            display_name: {},
            foo: {},
            turtles: {},
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="turtles" invisible="1">
                    <list>
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect("[name='p']").toHaveCount(0);
    expect.verifySteps(["get_views partner", "web_read partner"]);

    await contains("[name='foo'] input").edit("plop", { confirm: false });
    await clickSave();
    expect.verifySteps(["web_save partner"]);
});

test("can't select a record in a one2many", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row").click();
    expect(".o_data_row_selected").toHaveCount(0);
});

test("save a record after creating and editing a new invalid record in a one2many", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name" required="1"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=int_field] input").edit("3", { confirm: false });
    await clickSave();
    expect(".o_data_row.o_selected_row").toHaveCount(1, {
        message: "line should not have been removed and should still be in edition",
    });
    expect(".o_field_widget[name=name]").toHaveClass("o_field_invalid");
});

test("nested one2manys, multi page, onchange", async () => {
    Partner._records[2].int_field = 5;
    Partner._records[0].p = [2, 4]; // limit 1 -> record 4 will be on second page
    Partner._records[1].turtles = [1];
    Partner._records[2].turtles = [2];
    Turtle._records[0].turtle_int = 1;
    Turtle._records[1].turtle_int = 2;

    Partner._onChanges.int_field = function (obj) {
        expect.step("onchange");
        obj.p = [[5]];
        obj.p.push([1, 2, { turtles: [[5], [1, 1, { turtle_int: obj.int_field }]] }]);
        obj.p.push([1, 4, { turtles: [[5], [1, 2, { turtle_int: obj.int_field }]] }]);
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="p">
                    <list editable="bottom" limit="1" default_order="name">
                        <field name="name" />
                        <field name="int_field" />
                        <field name="turtles">
                            <list editable="bottom">
                                <field name="turtle_int"/>
                            </list>
                        </field>
                    </list>
                </field>
            </form>`,
        resId: 1,
        mode: "edit",
    });

    await contains(".o_field_widget[name=int_field] input").edit("5", { confirm: "blur" });
    expect.verifySteps(["onchange"]);

    await clickSave();
    expect(Partner._records[0].int_field).toBe(5);
    expect(Turtle._records[1].turtle_int).toBe(5);
    expect(Turtle._records[0].turtle_int).toBe(5);
});

test("multi page, command forget for record of second page", async () => {
    Partner._records[0].p = [1, 2, 4];
    Partner._onChanges = {
        int_field: function (obj) {
            obj.p = [[3, 4]];
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="p">
                        <list limit="2">
                            <field name="name"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect("[name=int_field] input").toHaveValue("10");
    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_cell")).toEqual(["first record", "second record"]);

    // trigger the onchange
    await contains("[name=int_field] input").edit("16", { confirm: "blur" });
    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_cell")).toEqual(["first record", "second record"]);
    expect(".o_x2m_control_panel .o_pager").toHaveCount(0);
});

test.tags("desktop");
test("multi page, command forget for record of second page on desktop", async () => {
    Partner._records[0].p = [1, 2, 4];
    Partner._onChanges = {
        int_field: function (obj) {
            obj.p = [[3, 4]];
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="p">
                        <list limit="2">
                            <field name="name"/>
                        </list>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-2 / 3");

    // trigger the onchange
    await contains("[name=int_field] input").edit("16", { confirm: "blur" });
    expect(".o_x2m_control_panel .o_pager_counter").toHaveCount(0);
});

test("new record, receive more create commands than limit", async () => {
    Partner._fields.sequence = fields.Integer();
    Partner._onChanges = {
        p: function (obj) {
            obj.p = [
                [0, 0, { sequence: 1, display_name: "Record 1" }],
                [0, 0, { sequence: 2, display_name: "Record 2" }],
                [0, 0, { sequence: 3, display_name: "Record 3" }],
                [0, 0, { sequence: 4, display_name: "Record 4" }],
            ];
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="p">
                        <list limit="2">
                            <field name="sequence"/>
                            <field name="display_name"/>
                        </list>
                    </field>
                </group>
            </form>`,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual([
        "Record 1",
        "Record 2",
        "Record 3",
        "Record 4",
    ]);
    expect(".o_x2m_control_panel .o_pager").toHaveCount(0);
});

test("active actions are passed to o2m field", async () => {
    Partner._records[0].turtles = [1, 2, 3];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="turtles">
                    <list editable="bottom" create="false" delete="false">
                        <field name="name" />
                        <field name="turtle_foo" />
                    </list>
                </field>
            </form>`,
        resId: 1,
        mode: "edit",
    });

    expect(".o_data_row").toHaveCount(3);
    expect(".o_list_record_remove").toHaveCount(0);

    await contains(".o_data_row:eq(2) .o_data_cell:eq(1)").click();

    expect(".o_data_row:eq(2)").toHaveClass("o_selected_row");

    await press("Enter");
    await animationFrame();

    expect(".o_data_row").toHaveCount(3);
    expect(".o_list_record_remove").toHaveCount(0);
    expect(".o_data_row:first-child").toHaveClass("o_selected_row");
});

test("kanban one2many in opened view form", async () => {
    Partner._records[0].p = [1];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="p">
                            <kanban class="o-custom-class" can_open="0">
                                <templates>
                                    <t t-name="card">
                                        <field name="name"/>
                                    </t>
                                </templates>
                            </kanban>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row td[name=name]").click();
    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".modal .o_field_x2many_kanban").toHaveClass("o-custom-class");

    await contains(".modal .o_kanban_record:not(.o_kanban_ghost)").click();
    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toBeFocused();

    await press("ArrowUp");
    await animationFrame();

    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
});

test("kanban one2many in opened view form (with _view_ref)", async () => {
    Partner._views = {
        [["kanban", 1234]]: /* xml */ `
            <kanban class="o-custom-class" can_open="0">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
    };
    Partner._records[0].p = [1];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="p" mode="kanban" context="{ 'kanban_view_ref': 1234 }" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row td[name=name]").click();
    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".modal .o_field_x2many_kanban").toHaveClass("o-custom-class");

    await contains(".modal .o_kanban_record:not(.o_kanban_ghost)").click();
    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toBeFocused();

    await press("ArrowUp");
    await animationFrame();

    expect(".modal .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
});

test("kanban one2many (with widget) in opened view form", async () => {
    Partner._records[0].p = [1];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name" widget="char"/>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record:eq(0)").toHaveText("first record");

    await contains(".o_kanban_record").click();
    expect(".o_dialog .o_form_view .o_field_widget[name=name]").toHaveCount(1);
    expect(".o_dialog .o_form_view .o_field_widget[name=name] input").toHaveValue("first record");
    expect(".o_kanban_record:eq(0)").toHaveText("first record");

    await contains(".o_dialog .o_form_view .o_field_widget[name=name] input").edit("test", {
        confirm: "blur",
    });
    expect(".o_kanban_record:eq(0)").toHaveText("test");
});

test.tags("desktop");
test("list one2many in opened view form", async () => {
    Partner._records[0].p = [1];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="p">
                            <list editable="bottom" class="o-custom-class">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row td[name=name]").click();
    expect(".modal .o_data_row td[name=name]").toHaveCount(1);
    expect(".modal .o_field_x2many_list").toHaveClass("o-custom-class");

    await contains(".modal thead th[data-name=name]").click();
    expect(".modal thead th[data-name=name]").toBeFocused();

    await press("ArrowUp");
    await animationFrame();

    expect(".modal .o_data_row td[name=name]").toHaveCount(1);
});

test.tags("desktop");
test("list one2many in opened view form (with _view_ref)", async () => {
    Partner._views = {
        [["list", 1234]]: /* xml */ `
            <list editable="bottom" class="o-custom-class">
                <field name="name"/>
            </list>
        `,
    };
    Partner._records[0].p = [1];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="p" mode="list" context="{ 'list_view_ref': 1234 }" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row td[name=name]").click();
    expect(".modal .o_data_row td[name=name]").toHaveCount(1);
    expect(".modal .o_field_x2many_list").toHaveClass("o-custom-class");

    await contains(".modal thead th[data-name=name]").click();
    expect(".modal thead th[data-name=name]").toBeFocused();

    await press("ArrowUp");
    await animationFrame();

    expect(".modal .o_data_row td[name=name]").toHaveCount(1);
});

test.tags("desktop");
test("one2many, form view dialog with custom footer", async () => {
    Partner._records[0].p = [1];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <footer>
                            <span class="my_span">Hello</span>
                        </footer>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td[name=name]").click();
    expect(".modal-footer .my_span").toHaveCount(1);

    await contains(".modal-header .btn-close").click();
    expect(".modal").toHaveCount(0);

    // open it again
    await contains(".o_data_row td[name=name]").click();
    expect(".modal-footer button").toHaveCount(0);
    expect(".modal-footer .my_span").toHaveCount(1);
});

test.tags("desktop");
test("one2many, form view dialog with added custom footer (replace='0')", async () => {
    Partner._records[0].p = [1];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <footer replace="0">
                            <button class="btn btn-primary my_button">Hello</button>
                        </footer>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_row td[name=name]").click();
    expect(".modal-footer .my_button").toHaveCount(1);
    expect(".modal-footer button").toHaveCount(3);

    await contains(".modal-header .btn-close").click();
    expect(".modal").toHaveCount(0);

    // open it again
    await contains(".o_data_row td[name=name]").click();
    expect(".modal-footer .my_button").toHaveCount(1);
    expect(".modal-footer button").toHaveCount(3);
});

test('Add a line, click on "Save & New" with an invalid form', async () => {
    mockService("notification", {
        add: (message, params) => {
            expect.step(params.type);
            expect(params.title).toBe("Invalid fields: ");
            expect(message.toString()).toBe("<ul><li>Name</li></ul>");
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="name" required="1"/>
                    </form>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(0);
    // Add a new record
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_dialog .o_form_view").toHaveCount(1);

    // Click on "Save & New" with an invalid form
    await contains(".o_dialog .o_form_button_save_new").click();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect.verifySteps(["danger"]);

    // Check that no buttons are disabled
    expect(".o_dialog .o_form_button_save_new").toBeEnabled();
    expect(".o_dialog .o_form_button_cancel").toBeEnabled();
});

test("field in list but not in fetched form", async () => {
    Partner._fields.o2m = fields.One2many({
        relation: "partner.type",
        relation_field: "p_id",
    });
    PartnerType._onChanges = {
        name: (rec) => {
            if (rec.name === "changed") {
                rec.color = 5;
            }
        },
    };

    PartnerType._fields.p_id = fields.Many2one({ relation: "partner" });
    PartnerType._views = { form: `<form><field name="name" /></form>` };
    onRpc((args) => {
        expect.step(`${args.method}: ${args.model}`);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="o2m">
                    <list>
                        <field name="name"/>
                        <field name="color" />
                    </list>
                </field>
            </form>`,
    });

    expect.verifySteps(["get_views: partner", "onchange: partner"]);
    await contains(".o_field_x2many_list_row_add a").click();
    expect.verifySteps(["get_views: partner.type", "onchange: partner.type"]);
    await contains(".modal .o_field_widget[name='name'] input").edit("changed", {
        confirm: "blur",
    });
    expect.verifySteps(["onchange: partner.type"]);
    await contains(".modal .o_form_button_save").click();
    expect(".o_data_row").toHaveText("changed 5");
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save: partner"]);
    expect(".o_data_row").toHaveText("changed 5");
});

test("pressing tab before an onchange is resolved", async () => {
    const onchangeGetPromise = new Deferred();

    Partner._onChanges = {
        name: (obj) => {
            obj.name = "test";
        },
    };
    onRpc("product", "onchange", async (args) => {
        if (args.args[2] === "name") {
            await onchangeGetPromise;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom" >
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    // This is not how it should happen but non trusted event listeners are called sooner than
    // trusted ones so the update is called after the list's tab listener in which case the field is
    // not dirty when we press tab, therefore we need to set it dirty through onChange before pressing tab
    // so in practice we could only run the following line but it wont work since the tab keydown event is not trusted
    // await contains(".o_field_widget[name='name'] input").edit("gold", { confirm: false });
    await contains(".o_field_widget[name='name'] input").edit("gold", { confirm: "blur" });
    await contains(".o_data_cell[name='name']").click(); // focus the input again

    await press("Tab");
    onchangeGetPromise.resolve();
    await animationFrame();

    expect(".o_data_row").toHaveCount(2);
});

test("add a row to an x2many and ask canBeRemoved twice", async () => {
    // This test simulates that the view is asked twice to save its changes because the user
    // is leaving. Before the corresponding fix, the changes in the x2many field weren't
    // removed after the save, and as a consequence they were saved twice (i.e. the row was
    // created twice).

    const def = new Deferred();
    Partner._views = {
        list: `<list><field name="int_field"/></list>`,
        search: `<search/>`,
        form: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    };

    onRpc("web_save", (args) => {
        expect.step("web_save");
        expect(args.args[1]).toEqual({
            p: [[0, args.args[1].p[0][1], { name: "a name" }]],
        });
    });
    onRpc("web_search_read", () => {
        return def;
    });

    const actions = [
        {
            id: 1,
            name: "test",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
        {
            id: 2,
            name: "another action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    ];

    await mountWithCleanup(WebClient);
    await getService("action").doAction(actions[0]);
    expect(".o_form_view").toHaveCount(1);

    // add a row in the x2many
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=name] input").edit("a name", { confirm: false });
    expect(".o_data_row").toHaveCount(1);

    getService("action").doAction(actions[1]);
    await animationFrame();
    getService("action").doAction(actions[1]);
    await animationFrame();
    expect.verifySteps(["web_save"]);

    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps([]);
});

test("one2many: save a record before the onchange is complete in a form dialog", async () => {
    Turtle._onChanges = {
        name: function () {},
    };

    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
            </form>`,
    };

    const def = new Deferred();
    onRpc("onchange", async (args) => {
        if (args.args[2].length === 1 && args.args[2][0] === "name") {
            await def;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="name" required="1"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);

    await contains(".o_field_widget[name=name] input").edit("new name", { confirm: false });
    await contains(".modal .o_form_button_save").click();
    expect(".modal").toHaveCount(1);

    def.resolve();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_row [name='name']")).toEqual(["donatello", "new name"]);
});

test("onchange create a record in an invisible x2many", async () => {
    Partner._onChanges = {
        foo: function () {},
    };
    Partner._records[0].p = [2];
    onRpc("onchange", () => {
        return {
            value: {
                p: [
                    [
                        1,
                        2,
                        {
                            name: "plop",
                            p: [[0, false, {}]],
                        },
                    ],
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="foo"/>
                <field name="p">
                    <list>
                        <field name="name" required="1"/>
                        <field name="p" invisible="1"/>
                    </list>
                </field>
            </form>`,
    });
    expect(queryAllTexts(".o_data_row")).toEqual(["second record"]);

    await contains(".o_field_widget[name=foo] input").edit("new foo value", { confirm: "blur" });
    expect(queryAllTexts(".o_data_row")).toEqual(["plop"]);
});

test("forget command for nested x2manys in form, not in list", async () => {
    expect.assertions(8);

    Partner._records[0].p = [1, 2];
    Partner._records[1].turtles = [2];
    Partner._onChanges = {
        int_field: function (obj) {
            obj.p = [
                [
                    1,
                    1,
                    {
                        foo: "new foo value (1)",
                        turtles: [
                            [
                                1,
                                2,
                                {
                                    turtle_foo: "new turtle foo value (1)",
                                    partner_ids: [[3, 4]],
                                },
                            ],
                        ],
                    },
                ],
                [
                    1,
                    2,
                    {
                        foo: "new foo value (2)",
                        turtles: [
                            [
                                1,
                                2,
                                {
                                    turtle_foo: "new turtle foo value (2)",
                                    partner_ids: [[3, 2]],
                                },
                            ],
                        ],
                    },
                ],
            ];
        },
    };
    onRpc("web_save", (args) => {
        expect(args.args[1]).toEqual({
            int_field: 16,
            p: [
                [
                    1,
                    1,
                    {
                        foo: "new foo value (1)",
                        turtles: [
                            [
                                1,
                                2,
                                {
                                    turtle_foo: "new turtle foo value (1)",
                                    partner_ids: [[3, 4]],
                                },
                            ],
                        ],
                    },
                ],
                [
                    1,
                    2,
                    {
                        foo: "new foo value (2)",
                        turtles: [
                            [
                                1,
                                2,
                                {
                                    turtle_foo: "new turtle foo value (2)",
                                    partner_ids: [[3, 2]],
                                },
                            ],
                        ],
                    },
                ],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="int_field"/>
                    <field name="p">
                        <list>
                            <field name="foo"/>
                        </list>
                        <form>
                            <field name="turtles">
                                <list editable="bottom">
                                    <field name="turtle_foo"/>
                                    <field name="partner_ids" widget="many2many_tags"/>
                                </list>
                            </field>
                        </form>
                    </field>
                </group>
            </form>`,
        resId: 1,
    });

    expect("[name=int_field] input").toHaveValue("10");

    // trigger the onchange
    await contains("[name=int_field] input").edit("16", { confirm: "blur" });
    expect("[name=foo]:eq(0)").toHaveText("new foo value (1)");
    expect("[name=foo]:eq(1)").toHaveText("new foo value (2)");

    // open the second x2many record
    await contains(".o_data_row:eq(1) td").click();
    expect(".o_dialog .o_data_row").toHaveCount(1);
    expect(".o_dialog .o_data_cell[name=turtle_foo]").toHaveText("new turtle foo value (2)");
    expect(".o_dialog .o_data_cell[name=partner_ids] .o_tag").toHaveCount(1);
    expect(".o_dialog .o_data_cell[name=partner_ids] .o_tag").toHaveText("aaa");

    await contains(".o_dialog .o_form_button_save").click();
    await clickSave();
});

test("modifiers based on x2many", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p" >
                    <list editable="bottom">
                        <field name="foo"/>
                    </list>
                </field>
                <field name="name" readonly="p"/>
                <field name="int_field" required="p"/>
                <button name="abc" string="Do it" class="my_button" invisible="not p"/>
            </form>`,
        resId: 1,
    });
    expect("button.my_button").toHaveCount(0);
    expect("[name='name'].o_readonly_modifier").toHaveCount(0);
    expect("[name='int_field'].o_required_modifier").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a").click();
    await contains("[name='foo'] input").edit("Test", { confirm: false });
    expect("button.my_button").toHaveCount(1);
    expect("[name='name'].o_readonly_modifier").toHaveCount(1);
    expect("[name='int_field'].o_required_modifier").toHaveCount(1);

    await contains("button.fa-trash-o").click();
    expect("button.my_button").toHaveCount(0);
    expect("[name='name'].o_readonly_modifier").toHaveCount(0);
    expect("[name='int_field'].o_required_modifier").toHaveCount(0);
});

test.tags("desktop");
test("add record in nested x2many with context depending on parent", async () => {
    expect.assertions(1);

    Partner._records[0].p = [1];
    onRpc("turtle", "web_read", (args) => {
        expect(args.kwargs.context).toEqual({
            allowed_company_ids: [1],
            bin_size: true,
            lang: "en",
            tz: "taht",
            uid: 7,
            x: 10,
            y: 2,
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="p">
                    <list editable="top">
                        <field name="turtles" widget="many2many_tags" context="{'x': parent.int_field, 'y': 2}"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click();
    await contains("div[name=turtles] .o-autocomplete.dropdown input").click();
    await contains(".o-autocomplete--dropdown-menu li a").click();
});

test("one2many with default_order on id, but id not in view", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        expect(args.args[1].turtles).toEqual([
            [1, 3, { turtle_int: 0 }],
            [1, 1, { turtle_int: 1 }],
            [1, 2, { turtle_int: 2 }],
        ]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top" default_order="turtle_int,id">
                        <field name="turtle_int" widget="handle"/>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);

    // drag the third record to top of the list
    await contains("tbody tr:eq(2) .o_handle_cell").dragAndDrop("tbody tr");
    await clickSave();

    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["kawa", "yop", "blip"]);
    expect.verifySteps(["get_views", "web_read", "web_save"]);
});

test("one2many causes an onchange on the parent which fails", async () => {
    Partner._onChanges = {
        turtles: function () {},
    };
    onRpc("partner", "onchange", () => {
        throw makeServerError();
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="top">
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_data_cell").click();
    expect(".o_field_widget[name='turtle_foo'] input").toHaveValue("blip");

    // onchange on parent record fails
    expect.errors(1);
    await contains(".o_field_widget[name='turtle_foo'] input").edit("new value", {
        confirm: "blur",
    });
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_data_cell[name='turtle_foo']").toHaveText("blip");
    expect(".o_error_dialog").toHaveCount(1);
});

test.tags("desktop");
test("one2many custom which can be edited in dialog or on the line", async () => {
    const customState = reactive({ isEditable: false });
    class CustomX2manyField extends X2ManyField {
        setup() {
            super.setup();
            this.canOpenRecord = true;
            this.customState = useState(customState);
        }

        get rendererProps() {
            const props = super.rendererProps;
            props.editable = this.customState.isEditable;
            return props;
        }
    }

    const customX2ManyField = {
        ...x2ManyField,
        component: CustomX2manyField,
    };
    registry.category("fields").add("custom", customX2ManyField);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" widget="custom">
                    <list editable="top">
                        <field name="turtle_foo"/>
                    </list>
                    <form>
                        <field name="name" />
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_form_status_indicator_buttons.invisible").toHaveCount(1, {
        message: "form view is not dirty",
    });

    await contains(".o_data_cell").click();
    expect(".modal").toHaveCount(1);

    customState.isEditable = true;
    await contains(".modal .btn-close").click();
    expect(".o_form_status_indicator_buttons.invisible").toHaveCount(1, {
        message: "form view is not dirty",
    });

    await contains(".o_data_cell").click();
    await contains("[name='turtle_foo'] input").edit("new value", { confirm: false });
    expect(".o_form_status_indicator_buttons:not(.invisible)").toHaveCount(1, {
        message: "form view is dirty",
    });
});

test("x2many kanban with float field in form (non inline) but not in kanban", async () => {
    // In this test, the form view contains an extra float field and isn't inline. When we open
    // a record, we add the form fields to the list of activeFields, and we load the
    // corresponding data (for that record only). Afterwards, we force a re-rendering of the
    // x2many kanban to ensure that the other record can still be rendered. Before the fix coming
    // with this test, it wasn't the case, because those records had extra activeFields, but no
    // entry in data for those fields.
    Partner._records[0].turtles = [2, 3];
    Turtle._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="turtle_qux"/>
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="turtles" invisible="not bar">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=turtles]").toHaveCount(1);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);

    // open the first record
    await contains(".o_kanban_record").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_field_widget[name=turtle_qux]").toHaveCount(1);

    // close the dialog
    await contains(".o_dialog .o_form_button_save").click();
    expect(".o_dialog").toHaveCount(0);

    // toggle bar to make the x2many invisible
    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_field_widget[name=turtles]").toHaveCount(0);

    // toggle bar again to make the x2many visible and force kanban cards to re-render
    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_field_widget[name=turtles]").toHaveCount(1);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
});

test("onchange on x2many returning an update command with only readonly fields", async () => {
    Partner._records[0].turtles = [2];
    Turtle._fields.name = fields.Char({ readonly: true });
    Partner._onChanges = {
        bar: (obj) => {
            obj.turtles = [[1, 2, { name: "onchange name" }]];
        },
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        expect(args.args[1]).toEqual({ bar: false }); // should not contain turtles
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="turtles">
                    <list><field name="name"/></list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("donatello");

    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_data_cell").toHaveText("onchange name");

    await clickSave();
    expect(".o_data_cell").toHaveText("donatello");
    expect.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
});

test("onchange on x2many returning a create command with only readonly fields", async () => {
    Turtle._fields.name = fields.Char({ readonly: true });
    Partner._onChanges = {
        bar: (obj) => {
            obj.turtles = [[0, false, { name: "onchange name" }]];
        },
    };
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("web_save", (args) => {
        expect(args.args[1]).toEqual({
            bar: false,
            turtles: [[0, args.args[1].turtles[0][1], {}]],
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="turtles">
                    <list><field name="name"/></list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("donatello");

    await contains(".o_field_widget[name=bar] input").click();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(2);
    expect(".o_data_cell:eq(1)").toHaveText("onchange name");

    await clickSave();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(2);
    expect.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
});

test("onchange on x2many add and delete x2m record, returning to initial state", async () => {
    Turtle._fields.name = fields.Char({ readonly: true });
    Partner._onChanges = {
        turtles: function () {},
    };

    let onchangeCount = 0;
    onRpc((args) => {
        expect.step(args.method);
    });
    onRpc("onchange", (args) => {
        if (onchangeCount === 1) {
            // partner turtles onchange for the new x2m record
            expect(args.model).toBe("partner");
            expect(Object.keys(args.args[1])).toEqual(["turtles"]);
            expect(args.args[1].turtles[0][0]).toBe(0);
            expect(args.args[2]).toEqual(["turtles"]);
        } else if (onchangeCount === 2) {
            // x2m record removed, empty list of commands expected
            expect(args.model).toBe("partner");
            expect(Object.keys(args.args[1])).toEqual(["turtles"]);
            expect(args.args[1].turtles).toEqual([]);
            expect(args.args[2]).toEqual(["turtles"]);
        }
        onchangeCount++;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("donatello");

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(2);
    await contains(".o_list_record_remove:eq(1)").click();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);

    await clickSave();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect.verifySteps(["get_views", "web_read", "onchange", "onchange", "onchange"]);
});

test("press TAB in editable='top' create='0' one2many list with lines generated by default_get -> onchange", async () => {
    onRpc((args) => {
        expect.step(args.method);
    });
    Partner._onChanges = { p: () => {} };

    onRpc("onchange", (args) => {
        expect.step(args.method);
        expect(args.args).toEqual([
            [],
            {},
            [],
            {
                display_name: {},
                p: {
                    fields: {
                        foo: {},
                    },
                    limit: 40,
                    order: "",
                },
            },
        ]);
        return {
            value: {
                p: [
                    [5], // delete all
                    [0, 0, { foo: "fu" }], // create new
                    [0, 0, { foo: "ber" }],
                    [0, 0, { foo: "qux" }],
                ],
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="top" create="0">
                        <field name="foo"/>
                    </list>
                </field>
            </form>`,
    });
    const target = getFixture();
    await contains('.o_data_cell[data-tooltip="ber"]').click();
    expect(target.querySelector(".o_selected_row .o_data_cell").dataset.tooltip).toBe("ber");
    await press("Tab");
    await animationFrame();
    expect(target.querySelector(".o_selected_row .o_data_cell").dataset.tooltip).toBe("qux");
    await press("Shift+Tab");
    await animationFrame();
    expect(target.querySelector(".o_selected_row .o_data_cell").dataset.tooltip).toBe("ber");
    await press("Shift+Tab");
    expect(target.querySelector(".o_selected_row .o_data_cell").dataset.tooltip).toBe("ber");
    expect.verifySteps(["get_views", "onchange"]);
});

test.tags("desktop");
test("expand record in dialog", async () => {
    Turtle._views["form, false"] = `<form><field name="name"/></form>`;
    mockService("action", {
        doAction(actionRequest) {
            expect.step([
                actionRequest.res_id,
                actionRequest.res_model,
                actionRequest.type,
                actionRequest.views,
            ]);
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="turtles"><list><field name="name"/></list></field></form>`,
        resId: 1,
    });
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(1);
    expect(".o_data_cell").toHaveText("donatello");
    await contains(queryFirst(".o_field_widget[name=turtles] .o_data_cell")).click();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(1);
    await contains(".o_dialog .modal-header .btn-close").click();
    await contains(".o_field_widget[name=turtles] .o_field_x2many_list_row_add a").click();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(0);
    await contains("[name='name'] input").edit("new turtle");
    await contains(".o_dialog .o_form_button_save").click();
    expect(".o_field_widget[name=turtles] .o_data_row").toHaveCount(2);
    await contains(".o_field_widget[name=turtles] .o_data_cell:last").click();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(0);
    await contains(".o_dialog .modal-header .btn-close").click();
    await clickSave();
    await contains(".o_field_widget[name=turtles] .o_data_cell:last").click();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(1);
    await contains(".o_dialog .modal-header .o_expand_button").click();
    expect.verifySteps([[4, "turtle", "ir.actions.act_window", [[false, "form"]]]]);
});

test("edit o2m with default_order on a field not in view", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_int">
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                    </list>
                    <form>
                        <field name="turtle_foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip", "kawa"]);

    await contains(".o_data_row:eq(1) .o_data_cell").click();
    await contains(".modal .o_field_widget[name=turtle_foo] input").edit("blip2");
    await contains(".modal-footer .o_form_button_save").click();
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["yop", "blip2", "kawa"]);
});

test("edit o2m with default_order on a field not in view (2)", async () => {
    Partner._records[0].turtles = [1, 2, 3];
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list default_order="turtle_foo,turtle_int">
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                    </list>
                    <form>
                        <field name="turtle_foo"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "kawa", "yop"]);

    await contains(".o_data_row:eq(1) .o_data_cell").click();
    await contains(".modal .o_field_widget[name=turtle_foo] input").edit("kawa2");
    await contains(".modal-footer .o_form_button_save").click();
    expect(queryAllTexts(".o_data_cell.o_list_char")).toEqual(["blip", "kawa2", "yop"]);
});
