import { describe, expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    middleClick,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    scroll,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickSave,
    contains,
    defineModels,
    editSearch,
    fields,
    getDropdownMenu,
    getFacetTexts,
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
    toggleMenuItem,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

class ResPartner extends models.Model {
    name = fields.Char({ string: "Res Partner Name" });

    _records = [
        {
            id: 1,
            name: "res partner",
        },
    ];
}

class Partner extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer({ sortable: true });
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
    trululu = fields.Many2one({ string: "Trululu", relation: "partner" });
    res_trululu = fields.Many2one({ string: "Res Trululu", relation: "res.partner" });
    timmy = fields.Many2many({ string: "pokemon", relation: "partner.type" });
    product_id = fields.Many2one({ string: "Product", relation: "product" });
    date = fields.Date({ string: "Some Date" });
    datetime = fields.Datetime({ string: "Datetime Field" });
    user_id = fields.Many2one({ string: "Users", relation: "res.users" });

    _records = [
        {
            id: 1,
            name: "first record",
            bar: true,
            foo: "yop",
            int_field: 10,
            p: [],
            turtles: [2],
            timmy: [],
            trululu: 4,
            res_trululu: 1,
            user_id: 1,
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            p: [],
            timmy: [],
            trululu: 1,
            product_id: 37,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            user_id: 1,
        },
        {
            id: 4,
            name: "aaa",
            bar: false,
        },
    ];
}

class Product extends models.Model {
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
    name = fields.Char();

    _records = [
        { id: 12, name: "gold" },
        { id: 14, name: "silver" },
    ];
}

class Turtle extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    turtle_foo = fields.Char({ string: "Foo" });
    turtle_bar = fields.Boolean({ string: "Bar", default: true });
    turtle_trululu = fields.Many2one({
        string: "Trululu",
        relation: "partner",
    });
    product_id = fields.Many2one({
        string: "Product",
        relation: "product",
        required: true,
    });
    partner_ids = fields.Many2many({ string: "Partner", relation: "partner" });

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
            partner_ids: [2, 4],
        },
        {
            id: 3,
            name: "raphael",
            product_id: 37,
            turtle_bar: false,
            turtle_foo: "kawa",
            partner_ids: [],
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
            id: 1,
            name: "Aline",
            partner_ids: [1, 2],
        },
        {
            id: 2,
            name: "Christine",
        },
    ];
}

defineModels([ResPartner, Partner, Product, PartnerType, Turtle, Users]);

test("many2ones in form views", async () => {
    expect.assertions(2);
    mockService("action", {
        doAction(params) {
            expect(params.res_id).toBe(17);
        },
        loadState() {},
    });

    Partner._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    onRpc("get_formview_action", function ({ args }) {
        expect(args[0]).toEqual([4]);
        return {
            res_id: 17,
            type: "ir.actions.act_window",
            target: "current",
            res_model: "res.partner",
        };
    });
    onRpc("get_formview_id", function ({ args }) {
        expect(args[0]).toEqual([4]);
        return false;
    });
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" string="custom label"/>
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_external_button:enabled", { visible: false }).click();
    expect(".o_dialog:not(.o_inactive_modal) .modal-title").toHaveText("Open: custom label");

    // TODO: test that we can edit the record in the dialog, and that
    // the value is correctly updated on close
});

test("editing a many2one, but not changing anything", async () => {
    expect.assertions(1);

    Partner._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };
    onRpc("get_formview_id", function ({ args }) {
        expect(args[0]).toEqual([4]);
        return false;
    });
    onRpc("web_save", () => {
        throw new Error("should not call write");
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="trululu"/>
                </sheet>
            </form>`,
    });

    // click on the external button (should do an RPC)
    await contains(".o_external_button", { visible: false }).click();
    // save and close modal
    await contains(".modal:eq(1) .o_form_button_save").click();
    // save form
    await clickSave();
});

test("context in many2one and default get", async () => {
    expect.assertions(2);

    Partner._fields.int_field.default = 14;
    Partner._fields.trululu.default = 2;

    onRpc("onchange", ({ args }) => {
        const context = args[3].trululu.context;
        expect(context.blip).toBe(undefined);
        expect(context.blop).toBe(3);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field" />
                <field name="trululu" context="{'blip': int_field, 'blop': 3}" />
            </form>`,
    });
});

test("do not send context in unity spec if field is invisible", async () => {
    expect.assertions(1);

    onRpc("web_read", ({ kwargs }) => {
        expect(kwargs.specification).toEqual({
            display_name: {},
            int_field: {},
            trululu: {
                fields: {},
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="int_field" />
                <field name="trululu" invisible="1" context="{'blip': int_field, 'blop': 3}" />
            </form>`,
    });
});

test("editing a many2one (with form view opened with external button)", async () => {
    expect.assertions(4);
    Partner._views = {
        form: `
            <form>
                <field name="foo" />
            </form>`,
    };

    onRpc("get_formview_id", () => false);
    onRpc("web_save", () => {
        expect.step("web_save");
    });
    onRpc("read", ({ args, model, kwargs }) => {
        if (model === "partner" && args[0][0] === 4) {
            expect.step(`read partner: ${args[1]}`);
            expect(kwargs.context.blip).toBe(10);
            expect(kwargs.context.blop).toBe(3);
        }
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="int_field" />
                    <field name="trululu" context="{'blip': int_field, 'blop': 3}"/>
                </sheet>
            </form>`,
    });

    // click on the external button (should do an RPC)
    await contains(".o_external_button", { visible: false }).click();

    await contains(".o_dialog:not(.o_inactive_modal) .o_field_widget[name='foo'] input").edit(
        "brandon"
    );

    // save and close modal
    await contains(".modal:eq(1) .o_form_button_save").click();
    expect.verifySteps(["web_save", "read partner: display_name"]);
    // save form
    await clickSave();
    expect.verifySteps([]);
});

test("many2ones in form views with show_address", async () => {
    onRpc("web_read", ({ kwargs }) => {
        if (kwargs.specification.trululu.context.show_address) {
            return [
                {
                    name: "",
                    trululu: { display_name: "aaa\nStreet\nCity ZIP" },
                },
            ];
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" context="{'show_address': 1}" />
                    </group>
                </sheet>
            </form>`,
    });

    expect("input.o_input").toHaveValue("aaa");
    expect(".o_field_many2one_extra").toHaveInnerHTML("<div>Street</div><div>City ZIP</div>", {
        type: "html",
    });
    expect("button.o_external_button").toHaveCount(1);
});

test("many2one show_address in edit", async () => {
    const namegets = {
        1: "first record\nFirst\nRecord",
        2: "second record\nSecond\nRecord",
        4: "aaa\nAAA\nRecord",
    };
    onRpc("web_read", ({ kwargs, parent }) => {
        if (kwargs.specification.trululu.context.show_address) {
            const result = parent();
            result[0].trululu = {
                id: result[0].trululu.id,
                display_name: namegets[result[0].trululu.id],
            };
            return result;
        }
    });
    onRpc("web_name_search", ({ parent }) => {
        const result = parent();
        return result.map(({ id }) => ({
            id,
            display_name: namegets[id],
            __formatted_display_name: namegets[id],
        }));
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" context="{'show_address': 1}" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("aaa");
    expect(".o_field_many2one_extra").toHaveInnerHTML("<div>AAA</div><div>Record</div>", {
        type: "html",
    });

    await contains(".o_field_widget input").edit("first record", { confirm: false });
    await runAllTimers();
    await contains(".dropdown-menu li").click();

    expect(".o_field_widget input").toHaveValue("first record");
    expect(".o_field_many2one_extra").toHaveInnerHTML("<div>First</div><div>Record</div>", {
        type: "html",
    });

    await contains(".o_field_widget input").edit("second record", { confirm: false });
    await runAllTimers();
    await contains(".dropdown-menu li").click();

    expect(".o_field_widget input").toHaveValue("second record");
    expect(".o_field_many2one_extra").toHaveInnerHTML("<div>Second</div><div>Record</div>", {
        type: "html",
    });
});

test("show_address works in a view embedded in a view of another type", async () => {
    expect.assertions(2);
    Turtle._records[1].turtle_trululu = 2;
    Turtle._views = {
        form: `
            <form>
                <field name="name" />
                <field name="turtle_trululu" context="{'show_address': 1}" />
            </form>`,
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    onRpc("turtle", "web_read", ({ kwargs }) => {
        expect(kwargs.specification.turtle_trululu.context).toEqual({
            show_address: 1,
        });
        return [
            {
                id: 1,
                name: "donatello",
                turtle_trululu: {
                    id: 2,
                    display_name: "second record\nrue morgue\nparis 75013",
                },
            },
        ];
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form edit="0">
                <field name="name" />
                <field name="turtles" />
            </form>`,
    });
    // click the turtle field, opens a modal with the turtle form view
    await contains(".o_data_row td.o_data_cell").click();

    expect('[name="turtle_trululu"]').toHaveText("second record\nrue morgue\nparis 75013");
});

test("many2ones in form views with search more", async () => {
    for (let i = 5; i < 11; i++) {
        Partner._records.push({ id: i, name: `Partner ${i}` });
    }
    Partner._fields.datetime.searchable = true;
    Partner._views = {
        search: `
            <search>
                <filter name="filter" string="Filter" domain="[[0, '=', 1]]"/>
            </search>`,
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" />
                    </group>
                </sheet>
            </form>`,
    });

    await selectFieldDropdownItem("trululu", "Search more...");

    expect("tr.o_data_row").toHaveCount(9);
    expect(".o_field_widget[name=trululu] input").toHaveValue("aaa");

    await toggleSearchBarMenu(".modal");
    await toggleMenuItem("Filter");

    expect("tr.o_data_row").toHaveCount(0);
});

test("many2ones: Open the selection dialog several times using the 'Search more...' button with a context containing 'search_default_...'", async () => {
    for (let i = 5; i < 11; i++) {
        Partner._records.push({ id: i, name: `Partner ${i}` });
    }
    Partner._fields.name.searchable = true;
    Partner._views = {
        search: `
            <search>
                <field name="name" />
            </search>`,
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" context="{ 'search_default_name': 'Partner 10'}"/>
                    </group>
                </sheet>
            </form>`,
    });

    await selectFieldDropdownItem("trululu", "Search more...");

    expect(".modal .o_data_row").toHaveCount(1);
    expect(getFacetTexts(".modal")).toEqual(["Displayed name\nPartner 10"]);

    await contains(".modal .btn-close").click();
    expect(".modal").toHaveCount(0);

    await selectFieldDropdownItem("trululu", "Search more...");
    expect(".modal .o_data_row").toHaveCount(1);
    expect(getFacetTexts(".modal")).toEqual(["Displayed name\nPartner 10"]);
});

test("many2ones in list views: create in dialog keeps the input", async () => {
    Partner._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    onRpc("web_save", ({ args }) => {
        expect.step(`web_save: ${JSON.stringify(args)}`);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="trululu" />
            </list>`,
    });

    await contains(".o_data_cell:eq(0)").click();
    await contains(".o_field_widget[name=trululu] input").edit("yy", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("trululu", "Create and edit...");

    await clickSave();
    expect.verifySteps([`web_save: [[],{"name":"yy"}]`]);
    expect(".o_field_widget[name=trululu] input").toHaveValue("yy");

    await contains(getFixture()).click();
    expect.verifySteps([`web_save: [[1],{"trululu":5}]`]);
    expect(".o_data_cell[name=trululu]:eq(0)").toHaveText("yy");
});

test("many2ones in list views: create a new record with a context", async () => {
    expect.assertions(6);
    onRpc("res.users", "name_create", ({ kwargs }) => {
        const { context } = kwargs;
        expect.step("name_create");
        expect(context.default_test).toBe(1);
        expect(context.test).toBe(2);
        expect(context).not.toInclude("default_yop");
        expect(context.yop).toBe(4);
    });
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="user_id" context="{'default_test': 1, 'test':2 }" />
            </list>`,
        context: {
            default_yop: 3,
            yop: 4,
        },
    });

    await contains(".o_data_cell:eq(0)").click();
    await contains(".o_field_widget[name=user_id] input").edit("yy", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("user_id", 'Create "yy"');
    expect(".o_external_button").toHaveCount(1);
    expect.verifySteps(["name_create"]);
});

test("using a many2one widget must take into account the decorations", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list>
                <field name="user_id" decoration-danger="int_field > 9" widget="many2one"/>
                <field name="int_field"/>
            </list>`,
    });

    expect(".o_list_many2one a.text-danger").toHaveCount(1);
    expect(".o_data_row").toHaveCount(3);
});

test("onchanges on many2ones trigger when editing record in form view", async () => {
    expect.assertions(2);
    Partner._onChanges = {
        user_id: () => {},
    };
    Users._fields.other_field = fields.Char({ string: "Other Field" });
    Users._views = {
        form: `
            <form>
                <field name="other_field" />
            </form>`,
    };
    onRpc("get_formview_id", () => false);
    onRpc("onchange", ({ args }) => {
        expect(args[1].user_id).toBe(1);
    });
    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="user_id"/>
                        </group>
                    </sheet>
                </form>`,
    });

    // open the many2one in form view and change something
    await contains(".o_external_button", { visible: false }).click();
    await contains(
        ".o_dialog:not(.o_inactive_modal) .o_field_widget[name='other_field'] input"
    ).edit("wood");

    // TODISCUSS ? Same record, don't change the display name (opti ?)
    // save the modal and make sure an onchange is triggered
    await contains(".modal:eq(1) .o_form_button_save").click();
    expect.verifySteps([
        "get_views",
        "web_read",
        "get_formview_id",
        "get_views",
        "web_read",
        "web_save",
        "read",
        "onchange",
    ]);
});

test("edit many2one before onchange is finished should not reset the value", async () => {
    Partner._onChanges = {
        name: function (obj) {
            obj.user_id = 19;
        },
    };
    onRpc("onchange", () => {
        expect.step("onchange");
        return def;
    });

    const def = new Deferred();
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="name"/>
                <field name="user_id"/>
            </form>`,
    });

    await contains("[name='name'] input").edit("new name");
    await contains("[name='user_id'] input").edit("Plop");
    expect("[name='user_id'] input").toHaveValue("Plop");

    def.resolve();
    await animationFrame();
    expect("[name='user_id'] input").toHaveValue("Plop");

    expect.verifySteps(["onchange"]);
});

test("many2one doesn't trigger field_change when being emptied", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list multi_edit="1">
                <field name="trululu"/>
            </list>`,
    });

    // Select two records
    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_field_widget[name=trululu] input").clear({ confirm: false });
    await runAllTimers();
    expect(".modal").toHaveCount(0);

    await contains(".o_field_widget[name=trululu] .ui-menu-item").click();
    expect(".modal").toHaveCount(1);
});

test("..._view_ref keys are removed from many2one context on create and edit", async () => {
    onRpc("get_views", ({ kwargs, method }) => {
        expect.step(
            JSON.stringify([method, kwargs.context.default_name, kwargs.context.form_view_ref])
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu"/>
                    </group>
                </sheet>
            </form>`,
        context: {
            form_view_ref: "test_form_view",
        },
    });

    expect.verifySteps(['["get_views",null,"test_form_view"]']);
    await contains(".o_field_widget[name=trululu] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name=trululu] .o_m2o_dropdown_option_create_edit").click();
    expect.verifySteps(['["get_views",null,null]']);
});

test("empty a many2one field in list view", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ trululu: false });
    });
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="trululu"/>
            </list>`,
    });

    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_field_widget[name=trululu] input").edit("");
    expect(".o_data_row .o_field_widget[name=trululu] input").toHaveText("");

    await contains(".o_list_view").click();
    expect(".o_data_row:eq(0)").toHaveText("");

    expect.verifySteps(["web_save"]);
});

test("focus tracking on a many2one in a list", async () => {
    Partner._views = {
        form: `
            <form>
                <field name="foo" />
            </form>`,
    };

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="trululu"/>
            </list>`,
    });

    // Select two records
    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_data_row .o_data_cell input").toBeFocused();

    await contains(".o_field_widget[name=trululu] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name=trululu] .o_m2o_dropdown_option_create_edit").click();

    // At this point, if the focus is correctly registered by the m2o, there
    // should be only one modal (the "Create" one) and none for saving changes.
    expect(".modal").toHaveCount(1);

    await contains(".o_form_button_cancel").click();

    expect(".o_data_row .o_data_cell input").toBeFocused();
    expect(".o_data_row .o_data_cell input").toHaveValue("");
});

test('many2one fields with option "no_open"', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" options="{'no_open': 1}" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget[name='trululu'] .o_external_button").toHaveCount(0);
});

test("empty many2one field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" />
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".dropdown-menu li.o_m2o_dropdown_option").toHaveCount(1);
    expect(".dropdown-menu li.o_m2o_start_typing").toHaveCount(0);

    await contains(".o_field_many2one[name='trululu'] input").edit("abc", { confirm: false });
    await runAllTimers();

    expect(".dropdown-menu li.o_m2o_dropdown_option").toHaveCount(2);
    expect(".dropdown-menu li.o_m2o_start_typing").toHaveCount(0);
    expect(".dropdown-menu li.o_m2o_no_result").toHaveCount(0);
});

test("empty readonly many2one field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="trululu" readonly="1"/></form>`,
    });

    expect("div.o_field_widget[name=trululu]").toHaveCount(1);
    expect(".o_field_widget[name=trululu] .o_many2one").toHaveText("");
});

test("empty many2one field with no result", async () => {
    patchWithCleanup(Many2XAutocomplete.prototype, {
        getCreationContext(value) {
            expect(value).toBe("");
            const context = super.getCreationContext(value);
            expect(context[`default_${this.props.nameCreateField}`]).toBe(undefined);
            return context;
        },
    });
    class M2O extends models.Model {
        m2o = fields.Many2one({ relation: "m2o" });
    }
    defineModels([M2O]);
    await mountView({
        type: "form",
        resModel: "m2o",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="m2o" />
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".dropdown-menu li.o_m2o_dropdown_option").toHaveCount(1);
    expect(".dropdown-menu li.o_m2o_dropdown_option").toHaveText("Create...");
    expect(".dropdown-menu li.o_m2o_start_typing").toHaveCount(0);

    await contains(".dropdown-menu li.o_m2o_dropdown_option").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_field_many2one[name=m2o] input").toHaveValue("");
    press("Esc");
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);

    await contains(".o_field_many2one input").edit("abc", { confirm: false });
    await runAllTimers();

    expect(".dropdown-menu li.o_m2o_dropdown_option").toHaveCount(2);
    expect(".dropdown-menu li.o_m2o_start_typing").toHaveCount(0);
    expect(".dropdown-menu li.o_m2o_no_result").toHaveCount(0);
});

test("empty many2one field with no result and no create & edit", async () => {
    class M2O extends models.Model {
        m2o = fields.Many2one({ relation: "m2o" });
    }
    defineModels([M2O]);
    await mountView({
        type: "form",
        resModel: "m2o",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="m2o" options="{'no_create_edit': 1}"/>
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".dropdown-menu li").toHaveCount(1);
    expect(".dropdown-menu li.o_m2o_start_typing").toHaveCount(1);

    await contains(".o_field_many2one input").edit("a", { confirm: false });
    await runAllTimers();

    expect(".dropdown-menu li").toHaveCount(1);
    expect(".dropdown-menu li.o_m2o_dropdown_option_create").toHaveCount(1);
});

test("empty many2one field with node options", async () => {
    expect.assertions(2);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" options="{'no_create_edit': 1}" />
                        <field name="product_id" options="{'no_create_edit': 1, 'no_quick_create': 1}" />
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one[name='trululu'] input").click();
    expect(".o_field_many2one[name='trululu'] .dropdown-menu li.o_m2o_start_typing").toHaveCount(0);

    await contains(".o_field_many2one[name='product_id'] input").click();
    expect(".o_field_many2one[name='product_id'] .dropdown-menu li.o_m2o_start_typing").toHaveCount(
        0
    );
});

test("many2one with no_create_edit and no_quick_create options should show no records when no result match", async () => {
    expect.assertions(2);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id" options="{'no_create_edit': 1, 'no_quick_create': 1}" />
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one[name='product_id'] input").click();
    expect(".o_field_many2one[name='product_id'] .dropdown-menu li.o_m2o_no_result").toHaveCount(0);
    await contains(".o_field_many2one[name='product_id'] input").edit("aze", { confirm: false });
    await runAllTimers();
    expect(".o_field_many2one[name='product_id'] .dropdown-menu li.o_m2o_no_result").toHaveCount(1);
});

test("many2one in edit mode", async () => {
    expect.assertions(17);

    // create 10 partners to have the 'Search more' option in the autocomplete dropdown
    for (let i = 0; i < 10; i++) {
        const id = 20 + i;
        Partner._records.push({ id, name: `Partner ${id}` });
    }

    Partner._views = {
        list: `
            <list>
                <field name="name" />
            </list>`,
        search: `
            <search>
                <field name="name" string="Name" />
            </search>`,
    };

    onRpc("partner", "web_save", ({ args }) => {
        expect(args[1].trululu).toBe(20);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu" />
                    </group>
                </sheet>
            </form>`,
    });

    await clickFieldDropdown("trululu");
    expect(".o_field_many2one[name='trululu'] .dropdown-menu").toBeVisible();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu li:not(.o_m2o_dropdown_option)"
    ).toHaveCount(8);
    expect(".o_field_many2one[name='trululu'] .dropdown-menu li.o_m2o_dropdown_option").toHaveCount(
        1
    );
    expect(".o_field_many2one[name='trululu'] .dropdown-menu li.o_m2o_start_typing").toHaveCount(0);

    await contains(".o_field_many2one[name='trululu'] input").click();
    expect(".o_field_many2one[name='trululu'] .dropdown-menu").toHaveCount(0);

    // change the value of the m2o with a suggestion of the dropdown
    await selectFieldDropdownItem("trululu", "first record");
    expect(".o_field_many2one[name='trululu'] .dropdown-menu").not.toHaveCount();
    expect(".o_field_many2one input").toHaveValue("first record");

    // change the value of the m2o with a record in the 'Search more' modal
    await clickFieldDropdown("trululu");
    // click on 'Search more' (mouseenter required by ui-autocomplete)
    await contains(
        ".o_field_many2one[name='trululu'] .dropdown-menu .o_m2o_dropdown_option_search_more"
    ).click();
    expect(".modal .o_list_view").toHaveCount(1);
    expect(".modal .o_list_view .o_list_record_selector").toHaveCount(0);
    expect(".modal .modal-footer .o_select_button").toHaveCount(0);
    expect(queryAll(".modal tbody tr").length).toBeGreaterThan(10, {
        message: "list should contain more than 10 records",
    });
    await contains(".modal .o_searchview_input").edit("P", { confirm: false });
    await runAllTimers();
    await press("Enter");
    await animationFrame();
    expect(".modal tbody tr").toHaveCount(10);
    // choose a record
    await contains(".modal .o_data_cell[data-tooltip='Partner 20']").click();
    expect(".modal").toHaveCount(0);
    expect(".o_field_many2one[name='trululu'] .dropdown-menu").not.toHaveCount();
    expect(".o_field_many2one input").toHaveValue("Partner 20");

    // save
    await clickSave();
    expect(".o_field_many2one input").toHaveValue("Partner 20");
});

test("many2one in non edit mode (with value)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form edit="0">
                <field name="res_trululu" />
                <field name="trululu" />
            </form>`,
    });

    expect("a.o_form_uri").toHaveCount(2);
    expect("div[name=res_trululu] a.o_form_uri").toHaveAttribute("href", "/odoo/res.partner/1");
    expect("div[name=trululu] a.o_form_uri").toHaveAttribute("href", "/odoo/m-partner/4");
});

test("many2one in non edit mode (without value)", async () => {
    Partner._records[0].trululu = false;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form edit="0">
                <field name="trululu" />
            </form>`,
    });

    // Remove value from many2one and then save, there should be no link anymore
    expect("a.o_form_uri").toHaveCount(0);
});

test("many2one with co-model whose name field is a many2one", async () => {
    Product._fields.name = fields.Many2one({
        string: "User Name",
        relation: "res.users",
    });
    Product._records = [
        {
            id: 37,
            name: 1,
        },
        {
            id: 41,
            name: 2,
        },
    ];
    Product._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" />
            </form>`,
    });

    await contains("div[name=product_id] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await contains("div[name=product_id] .o_m2o_dropdown_option_create_edit").click();
    expect(".modal .o_form_view").toHaveCount(1);

    // quick create 'new value'
    await contains(".modal div[name=name] input").edit("new value", { confirm: false });
    await runAllTimers();
    await contains(".modal div[name=name] .o_m2o_dropdown_option").click();
    expect(".modal div[name=name] input").toHaveValue("new value");

    await contains(".modal .o_form_button_save").click();
    expect(".modal .o_form_view").toHaveCount(0);
    expect("div[name=product_id] input").toHaveValue("new value");
});

test("many2one searches with correct value", async () => {
    onRpc("web_name_search", ({ kwargs }) => {
        expect.step(`search: ${kwargs.name}`);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="trululu" />
                </sheet>
            </form>`,
    });

    expect(".o_field_many2one input").toHaveValue("aaa");
    await contains(".o_field_many2one input").click();

    // unset the many2one -> should search again with ''
    await contains(".o_field_many2one input").clear({ confirm: false });
    await runAllTimers();

    await contains(".o_field_many2one input").edit("p", { confirm: false });
    await runAllTimers();

    // close and re-open the dropdown -> should search with 'p' again
    await contains(".o_field_many2one input").click();
    await runAllTimers();
    await contains(".o_field_many2one input").click();
    await runAllTimers();

    expect.verifySteps(["search: ", "search: ", "search: p", "search: p"]);
});

test("many2one search with trailing and leading spaces", async () => {
    onRpc("web_name_search", ({ kwargs }) => {
        expect.step("search: " + kwargs.name);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu" />
            </form>`,
    });

    const input = ".o_field_many2one[name='trululu'] input";
    await contains(input).click();

    expect(".o_field_many2one[name='trululu'] .dropdown-menu").toBeVisible();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu li:not(.o_m2o_dropdown_option)"
    ).toHaveCount(3);

    // search with leading spaces
    await contains(input).edit("   first", { confirm: false });
    await runAllTimers();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu li:not(.o_m2o_dropdown_option)"
    ).toHaveCount(1);

    // search with trailing spaces
    await contains(input).edit("first  ", { confirm: false });
    await runAllTimers();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu li:not(.o_m2o_dropdown_option)"
    ).toHaveCount(1);

    // search with leading and trailing spaces
    await contains(input).edit("   first   ", { confirm: false });
    await runAllTimers();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu li:not(.o_m2o_dropdown_option)"
    ).toHaveCount(1);

    expect.verifySteps(["search: ", "search: first", "search: first", "search: first"]);
});

// Should be removed ?
test("many2one field with option always_reload (edit)", async () => {
    onRpc("web_read", ({ parent }) => {
        const result = parent();
        result[0].trululu = {
            ...result[0].trululu,
            display_name: "first record\nand some address",
        };
        return result;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="trululu" />
            </form>`,
    });

    expect(".o_field_widget[name='trululu'] input").toHaveValue("first record");
    expect(".o_field_many2one_extra").toHaveCount(1);
    expect(".o_field_many2one_extra").toHaveText("and some address");
});

test("many2one field and list navigation", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="trululu"/>
            </list>`,
    });

    // edit first input, to trigger autocomplete
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_data_cell input").clear();

    // press keydown, to select first choice
    await press("arrowdown");

    // we now check that the dropdown is open (and that the focus did not go
    // to the next line)
    expect(".o_field_many2one").toHaveCount(1);
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_data_row:eq(1)").not.toHaveClass("o_selected_row");
});

test("standalone many2one field", async () => {
    class Comp extends Component {
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'coucou'" fields="fields" fieldNames="['partner_id']" values="values" mode="'edit'" t-slot-scope="scope">
                <Field name="'partner_id'" record="scope.record" canOpen="false" />
            </Record>
        `;
        static props = ["*"];
        setup() {
            this.fields = {
                partner_id: {
                    display_name: "partner_id",
                    type: "many2one",
                    relation: "partner",
                },
            };
            this.values = {
                partner_id: [1, "first partner"],
            };
        }
    }

    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountWithCleanup(Comp);

    await contains(".o_field_widget input").edit("xyzzrot", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget .o_m2o_dropdown_option_create").click();
    expect(".o_field_widget .o_external_button").toHaveCount(0);
    expect.verifySteps(["web_name_search", "name_create"]);
});

test("form: quick create then save directly", async () => {
    expect.assertions(3);

    const def = new Deferred();
    const newRecordId = 5; // with the current records, the created record will be assigned id 5
    onRpc("name_create", async () => {
        expect.step("name_create");
        await def;
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].trululu).toBe(newRecordId);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    await contains(".o_field_widget[name=trululu] input").edit("b", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create").click();
    await contains(".o_form_button_save").click();

    // should wait for the name_create before creating the record
    expect.verifySteps(["name_create"]);

    def.resolve();
    await animationFrame();

    expect.verifySteps(["web_save"]);
});

test("form: quick create for field that returns false after name_create call", async () => {
    onRpc("name_create", () => {
        expect.step("name_create");
        // Resolve the name_create call to false. This is possible if
        // _rec_name for the model of the field is unassigned.
        return false;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    await contains(".o_field_widget[name=trululu] input").edit("beam", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create").click();
    expect.verifySteps(["name_create"]);
    expect(".o_input_dropdown input").toHaveValue("");
});

test("list: quick create then save directly", async () => {
    expect.assertions(8);
    const def = new Deferred();
    const newRecordId = 5;

    onRpc("name_create", async () => {
        expect.step("name_create");
        await def;
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const values = args[1];
        expect(values.trululu).toBe(newRecordId);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="trululu" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(3);

    await contains(".o_control_panel_main_buttons .o_list_button_add").click();

    expect(".o_data_row").toHaveCount(4);

    await contains(".o_field_widget[name=trululu] input").edit("b", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create").click();

    await contains(".o_list_button_save").click();

    // should wait for the name_create before creating the record
    expect.verifySteps(["name_create"]);
    expect(".o_data_row").toHaveCount(4);

    def.resolve();
    await animationFrame();

    expect.verifySteps(["web_save"]);
    expect(".o_data_row").toHaveCount(4);
    expect(".o_data_row .o_data_cell:eq(0)").toHaveText("b");
});

test("list in form: quick create then save directly", async () => {
    expect.assertions(4);

    const def = new Deferred();
    const newRecordId = 5; // with the current records, the created record will be assigned id 5
    onRpc("name_create", async () => {
        expect.step("name_create");
        await def;
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].p[0][2].trululu).toBe(newRecordId);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="trululu" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".o_field_widget[name=trululu] input").edit("b", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create").click();

    await contains(".o_form_button_save").click();

    // should wait for the name_create before creating the record
    expect.verifySteps(["name_create"]);

    await def.resolve();
    await animationFrame();

    expect.verifySteps(["web_save"]);
    expect(".o_data_row .o_data_cell").toHaveText("b");
});

test("name_create in form dialog", async () => {
    onRpc("name_create", () => {
        expect.step("name_create");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <group>
                    <field name="p">
                        <list>
                            <field name="bar"/>
                        </list>
                        <form>
                            <field name="product_id"/>
                        </form>
                    </field>
                </group>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".modal .o_field_widget[name=product_id] input").edit("new record", {
        confirm: false,
    });
    await runAllTimers();
    await contains(".modal .o_field_widget[name=product_id] .o_m2o_dropdown_option_create").click();

    expect.verifySteps(["name_create"]);
});

test("many2one inside one2many form view, with domain", async () => {
    expect.assertions(4);

    Partner._fields.trululu.domain = "[['id', '<', 1000]]";
    Partner._records = [
        { id: 1, name: "a1", p: [1] },
        { id: 2, name: "a2" },
        { id: 3, name: "a3" },
        { id: 4, name: "a4" },
        { id: 5, name: "a5" },
        { id: 6, name: "a6" },
        { id: 7, name: "a7" },
        { id: 8, name: "a8" },
        { id: 9, name: "a9" },
    ];
    Partner._views = {
        list: '<list><field name="name"/></list>',
    };
    onRpc("web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["id", ">", 1]]);
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["id", ">", 1]]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list>
                            <field name="name"/>
                            <field name="trululu" domain="[]"/>
                        </list>
                        <form>
                            <field name="trululu" domain="[['id', '>', 1]]"/>
                        </form>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_field_widget[name=trululu] input").click();
    await runAllTimers();
    await clickFieldDropdownItem("trululu", "Search more...");

    expect(".modal .o_list_view").toHaveCount(1);
    expect(".modal .o_data_row").toHaveCount(8);
});

test("list in form: quick create then add a new line directly", async () => {
    // required many2one inside a one2many list: directly after quick creating
    // a new many2one value (before the name_create returns), click on add an item:
    // at this moment, the many2one has still no value, and as it is required,
    // the row is discarded if a saveLine is requested. However, it should
    // wait for the name_create to return before trying to save the line.
    expect.assertions(8);
    Partner._onChanges = {
        trululu: () => {},
    };

    const def = new Deferred();
    const newRecordId = 5; // with the current records, the created record will be assigned id 5
    onRpc("name_create", async () => {
        await def;
    });
    onRpc("web_save", ({ args }) => {
        expect(args[1].p[0][2].trululu).toBe(newRecordId);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="trululu" required="1" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".o_field_widget[name=trululu] input").edit("b", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create").click();

    await contains(".o_field_x2many_list_row_add a").click();

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row").toHaveClass("o_selected_row");

    def.resolve();
    await animationFrame();

    expect(".o_data_row .o_data_cell:eq(0)").toHaveText("b");
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:eq(1)").toHaveClass("o_selected_row");

    await clickSave();

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_data_cell").toHaveText("b");
});

test("list in form: create with one2many with many2one", async () => {
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [[0, 0, { name: "new record", p: [] }]],
    });
    onRpc("read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "name") {
            throw new Error("read(['name']) should not be called");
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="name" />
                            <field name="trululu" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect("td.o_data_cell:eq(0)").toHaveText("new record");
});

test("list in form: create with one2many with many2one (version 2)", async () => {
    // This test simulates the exact same scenario as the previous one,
    // except that the value for the many2one is explicitely set to false,
    // which is stupid, but this happens, so we have to handle it
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [[0, 0, { name: "new record", trululu: false, p: [] }]],
    });
    onRpc("read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "name") {
            throw new Error("read(['name']) should not be called");
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="name" />
                            <field name="trululu" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect("td.o_data_cell:eq(0)").toHaveText("new record");
});

test("item not dropped on discard with empty required field (default_get)", async () => {
    // This test simulates discarding a record that has been created with
    // one of its required field that is empty. When we discard the changes
    // on this empty field, it should not assume that this record should be
    // abandonned, since it has been added (even though it is a new record).
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [[0, 0, { name: "new record", trululu: false, p: [] }]],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="name" />
                            <field name="trululu" required="1" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect("tr.o_data_row").toHaveCount(1);
    expect("td.o_data_cell:eq(0)").toHaveText("new record");
    expect("td.o_data_cell:eq(1)").toHaveText("");
    await contains(".o_data_row .o_data_cell").click();
    expect(".o_selected_row .o_data_cell:eq(1)").toHaveClass("o_required_modifier");

    // discard by clicking on body
    await contains(getFixture()).click();

    expect("tr.o_data_row").toHaveCount(1);
    expect("td.o_data_cell:eq(0)").toHaveText("new record");
    expect("td.o_data_cell:eq(1)").toHaveText("");

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_selected_row .o_data_cell:eq(1)").toHaveClass("o_required_modifier");
});

test("list in form: read with unique ids (default_get)", async () => {
    Partner._records[0].name = "MyTrululu";
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [
            [0, 0, { trululu: 1, p: [] }],
            [0, 0, { trululu: 1, p: [] }],
        ],
    });
    onRpc("read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "name") {
            throw new Error("read(['name']) should not called");
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom">
                            <field name="trululu" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect(queryAllTexts("td.o_data_cell")).toEqual(["MyTrululu", "MyTrululu"]);
});

test("list in form: show name of many2one fields in multi-page (default_get)", async () => {
    Partner._fields.p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        relation_field: "trululu",
        default: [
            [0, 0, { name: "record1", trululu: 1, p: [] }],
            [0, 0, { name: "record2", trululu: 2, p: [] }],
        ],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p">
                        <list editable="bottom" limit="1">
                            <field name="name" />
                            <field name="trululu" />
                        </list>
                    </field>
                </sheet>
            </form>`,
    });

    expect(queryAllTexts("td.o_data_cell")).toEqual([
        "record1",
        "first record",
        "record2",
        "second record",
    ]);
});

test("list in form: item not dropped on discard with empty required field (onchange in default_get)", async () => {
    // variant of the test "list in form: discard newly added element with
    // empty required field (default_get)", in which the `default_get`
    // performs an `onchange` at the same time. This `onchange` may create
    // some records, which should not be abandoned on discard, similarly
    // to records created directly by `default_get`
    Partner._fields.product_id = fields.Many2one({
        string: "Product",
        relation: "product",
        default: 37,
        onChange: (obj) => {
            if (obj.product_id === 37) {
                obj.p = [[0, 0, { name: "entry", trululu: false }]];
            }
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" />
                <field name="p">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="trululu" required="1" />
                    </list>
                </field>
            </form>`,
    });

    // check that there is a record in the editable list with empty string as required field
    expect(".o_data_row").toHaveCount(1);
    expect("td.o_data_cell:eq(0)").toHaveText("entry");
    expect("td.o_data_cell.o_required_modifier").toHaveCount(1);
    expect("td.o_data_cell.o_required_modifier").toHaveText("");

    // click on empty required field in editable list record
    await contains("td.o_data_cell.o_required_modifier").click();
    // click off so that the required field still stay empty
    await contains(getFixture()).click();

    // record should not be dropped
    expect(".o_data_row").toHaveCount(1);
    expect("td.o_data_cell:eq(0)").toHaveText("entry");
    expect("td.o_data_cell.o_required_modifier").toHaveText("");
});

test("list in form: item not dropped on discard with empty required field (onchange on list after default_get)", async () => {
    // discarding a record from an `onchange` in a `default_get` should not
    // abandon the record. This should not be the case for following
    // `onchange`, except if an onchange make some changes on the list:
    // in particular, if an onchange make changes on the list such that
    // a record is added, this record should not be dropped on discard
    Partner._onChanges = {
        product_id: (obj) => {
            if (obj.product_id === 37) {
                obj.p = [[0, 0, { name: "entry", trululu: false }]];
            }
        },
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" />
                <field name="p">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="trululu" required="1" />
                    </list>
                </field>
            </form>`,
    });

    // check no record in list
    expect(".o_data_row").toHaveCount(0);

    // select product_id to force on_change in editable list
    await contains("div[name=product_id] input").click();
    await contains(".ui-menu-item").click();

    // check that there is a record in the editable list with empty string as required field
    expect(".o_data_row").toHaveCount(1);

    expect("td.o_data_cell:eq(0)").toHaveText("entry");
    expect("td.o_required_modifier").toHaveCount(1);
    expect("td.o_required_modifier").toHaveText("");

    // click on empty required field in editable list record
    await contains("td.o_required_modifier").click();
    // click off so that the required field still stay empty
    await contains(getFixture()).click();

    // record should not be dropped
    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts("td.o_data_cell")).toEqual(["entry", ""]);
});

test('item dropped on discard with empty required field with "Add an item" (invalid on "ADD")', async () => {
    // when a record in a list is added with "Add an item", it should
    // always be dropped on discard if some required field are empty
    // at the record creation.
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="trululu" required="1" />
                    </list>
                </field>
            </form>`,
    });

    // Click on "Add an item"
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_field_widget.o_required_modifier[name=trululu]").toHaveCount(1);
    expect(".o_field_widget.o_required_modifier[name=trululu] input").toHaveValue("");

    // click on empty required field in editable list record
    await contains(".o_field_widget.o_required_modifier[name=trululu] input").click();
    // click off so that the required field still stay empty
    await contains(getFixture()).click();

    // record should be dropped
    expect(".o_data_row").toHaveCount(0);
});

test('item not dropped on discard with empty required field with "Add an item" (invalid on "UPDATE")', async () => {
    // when a record in a list is added with "Add an item", it should
    // be temporarily added to the list when it is valid (e.g. required
    // fields are non-empty). If the record is updated so that the required
    // field is empty, and it is discarded, then the record should not be
    // dropped.
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="trululu" required="1" />
                    </list>
                </field>
            </form>`,
    });

    expect(".o_data_row").toHaveCount(0);

    // Click on "Add an item"
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_data_row").toHaveCount(1);

    expect(".o_field_widget.o_required_modifier[name=trululu] input").toHaveCount(1);
    expect(".o_field_widget.o_required_modifier[name=trululu] input").toHaveValue("");

    // add something to required field and leave edit mode of the record
    await contains(".o_field_widget.o_required_modifier[name=trululu] input").click();
    await contains("li.ui-menu-item").click();
    await contains(getFixture()).click();

    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_cell:eq(1)").toHaveText("first record");

    // leave edit mode of the record
    await contains(getFixture()).click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_cell:eq(1)").toHaveText("first record");
});

// WARNING: this does not seem to be a many2one field test
test("list in form: default_get with x2many create", async () => {
    expect.assertions(3);

    Partner._fields.timmy = fields.Many2many({
        string: "pokemon",
        relation: "partner.type",
        default: [[0, 0, { name: "brandon is the new timmy" }]],
        onChange: (obj) => {
            obj.int_field = obj.timmy.length;
        },
    });

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            int_field: 1,
            timmy: [[0, args[1].timmy[0][1], { name: "new value" }]],
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="timmy">
                        <list editable="bottom">
                            <field name="name" />
                        </list>
                    </field>
                    <field name="int_field" />
                </sheet>
            </form>`,
    });

    expect("td.o_data_cell").toHaveText("brandon is the new timmy");
    expect(".o_field_integer input").toHaveValue("1");

    // edit the subrecord and save
    await contains(".o_data_cell").click();
    await contains(".o_data_cell input").edit("new value", { confirm: false });
    await clickSave();
});

// WARNING: this does not seem to be a many2one field test
test("list in form: default_get with x2many create and onchange", async () => {
    expect.assertions(1);
    Partner._fields.turtles = fields.One2many({
        string: "one2many turtle field",
        relation: "turtle",
        relation_field: "turtle_trululu",
        default: [
            [4, 2],
            [4, 3],
        ],
    });

    onRpc("web_save", ({ args }) => {
        expect(args[1].turtles).toEqual([
            [4, 2],
            [4, 3],
        ]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="turtles">
                        <list editable="bottom">
                            <field name="turtle_foo" />
                        </list>
                    </field>
                    <field name="int_field" />
                </sheet>
            </form>`,
    });

    await clickSave();
});

test("list in form: call button in sub view", async () => {
    Partner._records[0].p = [2];
    Product._views = {
        form: `
            <form>
                <header>
                    <button name="action" type="action" string="Just do it !" />
                    <button name="object" type="object" string="Just don't do it !" />
                    <field name="name" />
                </header>
            </form>`,
    };

    const def = new Deferred();
    mockService("action", {
        doActionButton(params) {
            const { name, resModel, resId, resIds } = params;
            expect.step(name);
            expect(resModel).toBe("product");
            expect(resId).toBe(37);
            expect(resIds).toEqual([37]);
            return def.then(() => {
                params.onClose();
            });
        },
    });
    onRpc("get_formview_id", () => false);

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="product_id"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".modal").toHaveCount(1);
    await contains("td.o_data_cell").click();
    await contains(".o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);

    const buttons = queryAll(".o_dialog:not(.o_inactive_modal) .o_form_statusbar button");

    await contains(buttons[0]).click();
    expect.verifySteps(["action"]);
    expect(buttons[1]).not.toBeEnabled();

    def.resolve();
    await animationFrame();

    await contains(".modal:eq(1) .o_form_button_cancel").click();
    expect(".modal").toHaveCount(1);

    await contains(".o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);

    await contains(".o_dialog:not(.o_inactive_modal) .o_form_statusbar button:eq(1)").click();
    expect.verifySteps(["object"]);
});

test("X2Many sequence list in modal", async () => {
    Partner._fields.sequence = fields.Integer({
        string: "Sequence",
        type: "integer",
        onChange: (obj) => {
            if (obj.id === 2) {
                obj.sequence = 1;
                expect.step("onchange sequence");
            }
        },
    });
    Partner._records[0].sequence = 1;
    Partner._records[1].sequence = 2;

    Product._fields.turtle_ids = fields.One2many({
        string: "Turtles",
        relation: "turtle",
    });
    Product._records[0].turtle_ids = [1];
    Product._records[0].name = "leonardo";
    Product._records[0].name = "xphone";

    Turtle._fields.partnertypes_ids = fields.One2many({
        string: "Partner",
        relation: "partner",
    });
    Turtle._fields.type_id = fields.Many2one({
        string: "Partner Type",
        relation: "partner.type",
    });
    Turtle._records[0].type_id = 12;

    PartnerType._fields.partner_ids = fields.One2many({
        string: "Partner",
        relation: "partner",
    });
    PartnerType._records[0].partner_ids = [1, 2];

    PartnerType._views = {
        form: `
            <form>
                <field name="partner_ids" />
            </form>`,
    };
    Partner._views = {
        list: `
            <list>
                <field name="name" />
                <field name="sequence" widget="handle" />
            </list>`,
    };

    onRpc("partner.type", "get_formview_id", () => false);
    onRpc("partner.type", "web_save", () => {
        expect.step("partner.type web_save");
    });
    await mountViewInDialog({
        type: "form",
        resModel: "product",
        resId: 37,
        arch: `
            <form>
                <field name="name" />
                <field name="turtle_ids" widget="one2many">
                    <list editable="bottom">
                        <field name="type_id"/>
                    </list>
                </field>
            </form>`,
    });

    expect(".modal").toHaveCount(1);

    await contains(".o_data_cell").click();
    await contains(".o_external_button", { visible: false }).click();

    expect(".modal").toHaveCount(2);
    expect(".modal:eq(1) .ui-sortable-handle").toHaveCount(2);

    await contains(
        ".o_dialog:not(.o_inactive_modal) .o_data_row:nth-child(2) .ui-sortable-handle"
    ).dragAndDrop(".o_dialog:not(.o_inactive_modal) tbody tr");

    // Saving the modal and then the original model
    await contains(".modal:eq(1) .o_form_button_save").click();
    await clickSave();

    expect.verifySteps(["onchange sequence", "partner.type web_save"]);
});

test("autocompletion in a many2one, in form view with a domain", async () => {
    expect.assertions(1);
    onRpc("web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        domain: [["trululu", "=", 4]],
        arch: '<form><field name="product_id" /></form>',
    });
    await contains(".o_field_widget[name=product_id] input").click();
});

test("autocompletion in a many2one, in form view with a date field", async () => {
    expect.assertions(1);
    onRpc("web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["bar", "=", true]]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="bar" />
                <field name="date" />
                <field name="trululu" domain="[('bar', '=', True)]" />
            </form>`,
    });
    await contains(".o_field_widget[name='trululu'] input").click();
});

test("creating record with many2one with option always_reload", async () => {
    Partner._fields.trululu = fields.Many2one({
        string: "Trululu",
        relation: "partner",
        default: 1,
        onChange: (obj) => {
            obj.trululu = 2; //[2, "second record"];
        },
    });

    onRpc("onchange", ({ parent }) => {
        const result = parent();
        result.value.trululu = {
            ...result.value.trululu,
            display_name: "hello world\nso much noise",
        };
        return result;
    });
    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu" />
            </form>`,
    });

    expect(".o_field_widget[name='trululu'] input").toHaveValue("hello world");
    expect.verifySteps(["get_views", "onchange"]);
});

test("empty list with sample data and many2one with option always_reload", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list sample="1">
                <field name="product_id" />
            </list>`,
        context: { search_default_empty: true },
        searchViewArch: `
            <search>
                <filter name="empty" domain="[('id', '&lt;', 0)]"/>
            </search>`,
    });

    expect(".o_list_view .o_content").toHaveClass("o_view_sample_data");
    expect(".o_list_table").toHaveCount(1);
    expect(".o_data_row").toHaveCount(10);
    expect("thead tr th").toHaveCount(2);
});

test("selecting a many2one, then discarding", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="product_id" /></form>',
    });
    expect(".o_field_widget[name='product_id'] input").toHaveValue("");

    await contains(".o_field_widget[name='product_id'] input").click();
    await contains(".o_field_widget[name='product_id'] .dropdown-item").click();
    expect(".o_field_widget[name='product_id'] input").toHaveValue("xphone");

    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name='product_id'] input").toHaveValue("");
});

test("domain and context are correctly used when doing a web_name_search in a m2o", async () => {
    expect.assertions(4);

    Partner._records[0].timmy = [12];
    // Need to take into account the company service which populates context at startup
    const DEFAULT_USER_CTX = { ...user.context, allowed_company_ids: [1] };
    serverState.userContext = { hey: "ho" };
    onRpc("product", "web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual(["&", ["foo", "=", "bar"], ["foo", "=", "yop"]]);
        expect(kwargs.context).toEqual({
            ...DEFAULT_USER_CTX,
            hey: "ho",
            hello: "world",
            test: "yop",
        });
        return [];
    });
    onRpc("partner", "web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["id", "in", [12]]]);
        expect(kwargs.context).toEqual({
            ...DEFAULT_USER_CTX,
            hey: "ho",
            timmy: [12],
        });
        return [];
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="product_id" domain="[('foo', '=', 'bar'), ('foo', '=', foo)]" context="{'hello': 'world', 'test': foo}" />
                <field name="foo" />
                <field name="trululu" context="{'timmy': timmy}" domain="[('id', 'in', timmy)]" />
                <field name="timmy" widget="many2many_tags" invisible="1" />
            </form>`,
    });

    await contains(".o_field_widget[name='product_id'] input").click();
    await contains(".o_field_widget[name='trululu'] input").click();
});

test("quick create on a many2one", async () => {
    expect.assertions(1);
    onRpc("name_create", ({ args }) => {
        expect(args[0]).toBe("new partner");
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" />
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").edit("new partner", { confirm: false });
    await runAllTimers();
    await press("tab");
});

test("failing quick create on a many2one because ValidationError", async () => {
    expect.assertions(5);

    Product._views = {
        form: '<form><field name="name" /></form>',
    };

    onRpc("name_create", () => {
        throw makeServerError({ type: "ValidationError" });
    });
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ name: "xyz" });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="product_id" /></form>',
    });

    await contains(".o_field_widget[name='product_id'] input").edit("abcd", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name='product_id'] .o_m2o_dropdown_option_create").click();
    await animationFrame(); // wait for the error service to ensure that there's no error dialog
    expect(".o_error_dialog").toHaveCount(0);
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_field_widget[name='name'] input").toHaveValue("abcd");

    await contains(".modal .o_field_widget[name='name'] input").edit("xyz");
    await contains(".modal .o_form_button_save").click();
    expect(".o_field_widget[name='product_id'] input").toHaveValue("xyz");
});

test("failing quick create on a many2one", async () => {
    expect.assertions(3);
    Product._views = {
        form: '<form><field name="name" /></form>',
    };
    onRpc("name_create", () => {
        throw makeServerError();
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="product_id" /></form>',
    });

    await contains(".o_field_widget[name='product_id'] input").edit("abcd", { confirm: false });
    await runAllTimers();
    expect.errors(1);
    await contains(".o_field_widget[name='product_id'] .o_m2o_dropdown_option_create").click();
    await animationFrame(); // wait for the error service
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_error_dialog").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(0);
});

test("failing quick create on a many2one inside a one2many because ValidationError", async () => {
    expect.assertions(4);

    Partner._views = {
        list: `
            <list editable="bottom">
                <field name="product_id" />
            </list>`,
    };
    Product._views = {
        form: '<form><field name="name" /></form>',
    };

    onRpc("name_create", () => {
        throw makeServerError({ type: "ValidationError" });
    });
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ name: "xyz" });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="p" /></form>',
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name='product_id'] input").edit("abcd", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name='product_id'] .o_m2o_dropdown_option_create").click();

    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_field_widget[name='name'] input").toHaveValue("abcd");

    await contains(".modal .o_field_widget[name='name'] input").edit("xyz");
    await contains(".modal .o_form_button_save").click();
    expect(".o_field_widget[name='product_id'] input").toHaveValue("xyz");
});

test("slow create on a many2one", async () => {
    Product._views = {
        form: '<form><field name="name" /></form>',
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" options="{'no_quick_create': 1}" />
                </sheet>
            </form>`,
    });
    await contains(".o_field_many2one input").edit("new product", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();

    expect(".modal").toHaveCount(1);
    // cancel the many2one creation with Discard button
    await contains(".modal .modal-footer .btn:not(.btn-primary)").click();
    expect(".modal").toHaveCount(0);
    expect(".o_field_many2one input").toHaveValue("");

    // cancel the many2one creation with Close button
    await contains(".o_field_many2one input").edit("new product", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();

    expect(".modal").toHaveCount(1);
    await contains(".modal .modal-header button").click();
    expect(".o_field_many2one input").toHaveValue("");
    expect(".modal").toHaveCount(0);

    // select a new value then cancel the creation of the new one --> restore the previous
    await contains(".o_field_widget[name=product_id] input").click();
    await contains(".ui-menu-item").click();
    expect(".o_field_many2one input").toHaveValue("xphone");

    await contains(".o_field_many2one input").edit("new product", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();
    expect(".modal").toHaveCount(1);

    await contains(".modal .modal-footer .btn:not(.btn-primary)").click();
    expect(".o_field_many2one input").toHaveValue("");

    // confirm the many2one creation
    await contains(".o_field_many2one input").edit("new product", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();

    expect(".modal .o_form_view").toHaveCount(1);

    await contains(".modal .o_form_button_cancel").click();
});

test("select a many2one value by pressing tab", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="product_id" /></form>',
    });

    await contains(".o_field_many2one input").edit("xph", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();

    expect(".modal").toHaveCount(0);
    expect(".o_field_many2one input").toHaveValue("xphone");
    expect(".o_external_button").toHaveCount(1);
});

test("no_create option on a many2one", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" options="{'no_create': 1}" />
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").edit("new partner", { confirm: false });
    await runAllTimers();
    expect(".o_m2o_dropdown_option_create").toHaveCount(0);
    expect(".o_m2o_dropdown_option_create_edit").toHaveCount(0);
    await press("escape");
});

test("no_create option on a many2one when can_create is absent", async () => {
    Partner._fields.product_id.readonly = true;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" options="{'no_create': 1}" readonly="0" />
                </sheet>
            </form>`,
    });
    await contains(".o_field_many2one input").edit("new partner", { confirm: false });
    await runAllTimers();
    expect(".o_m2o_dropdown_option_create").toHaveCount(0);
    expect(".o_m2o_dropdown_option_create_edit").toHaveCount(0);
    await press("escape");
});

test("no_quick_create option on a many2one when can_create is absent", async () => {
    Partner._fields.product_id.readonly = true;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" options="{'no_quick_create': 1}" readonly="0" />
                </sheet>
            </form>`,
    });
    await contains(".o_field_many2one input").edit("new partner", { confirm: false });
    await runAllTimers();
    expect(queryAllTexts(".ui-autocomplete .o_m2o_dropdown_option")).toEqual([
        "Create and edit...",
    ]);
});

test("can_create and can_write option on a many2one", async () => {
    Product.options = {
        can_create: "false",
        can_write: "false",
    };
    Product._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    onRpc("product", "get_formview_id", () => false);

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" can_create="false" can_write="false"/>
                </sheet>
            </form>`,
    });

    expect(".modal").toHaveCount(1);

    await contains(".o_field_many2one input").click();
    expect(".o_m2o_dropdown_option.o_m2o_dropdown_option_create").toHaveCount(0);

    await contains(".ui-menu-item:eq(1)").click();
    expect(".o_field_many2one input").toHaveValue("xpad");
    expect(".o_field_many2one .o_external_button").toHaveCount(1);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);
    expect(".modal .o_form_view .o_form_readonly").toHaveCount(1);

    await contains(".o_dialog:not(.o_inactive_modal) .modal-footer .btn-primary").click();

    await contains(".o_field_many2one input").edit("new product");
    expect(".modal").toHaveCount(1);
});

test("create_name_field option on a many2one", async () => {
    // when the 'create_name_field' option is set, the value entered in the
    // many2one input should be used to populate this specified field,
    // instead of the generic 'name' field.
    Partner._views = {
        form: `
            <form>
                <field name="foo" />
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="trululu" options="{'create_name_field': 'foo'}" />
                </sheet>
            </form>`,
    });

    await contains(".o_field_widget[name=trululu] input").edit("yz", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name=trululu] input").click();
    await selectFieldDropdownItem("trululu", "Create and edit...");

    expect(".o_field_widget[name=foo] input").toHaveValue("yz");

    await contains(".o_form_button_cancel").click();
});

test("propagate can_create onto the search popup", async () => {
    Product._records = [
        { id: 1, name: "Tromblon1" },
        { id: 2, name: "Tromblon2" },
        { id: 3, name: "Tromblon3" },
        { id: 4, name: "Tromblon4" },
        { id: 5, name: "Tromblon5" },
        { id: 6, name: "Tromblon6" },
        { id: 7, name: "Tromblon7" },
        { id: 8, name: "Tromblon8" },
        ...Product._records,
    ];
    Product._views = {
        list: `
            <list>
                <field name="name"/>
            </list>`,
        search: `
            <search>
                <field name="name"/>
            </search>`,
    };
    onRpc("get_formview_id", () => false);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="name"/>
                <field name="product_id" can_create="false"/>
            </form>`,
    });

    await contains(".o_field_widget[name=product_id] input").click();

    expect(".o-autocomplete a:contains(Start typing...)").toHaveCount(0);

    await contains(".o_field_widget[name=product_id] input").edit("a", { confirm: false });
    await runAllTimers();

    expect(".ui-autocomplete a:contains(Create and Edit)").toHaveCount(0);

    await contains(".o_field_many2one[name=product_id] input").edit("", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("product_id", "Search more...");

    expect(".modal-dialog.modal-lg").toHaveCount(1);

    expect(queryAllTexts(".modal-footer button")).toEqual(["Close"]);
});

test("many2one with can_create=false shows no result item when searched something that doesn't exist", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" can_create="false" can_write="false" />
                </sheet>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    await contains(".o_field_many2one[name=product_id] input").edit("abc", { confirm: false });
    await runAllTimers();
    expect(".o_field_many2one[name=product_id] .o_m2o_dropdown_option_create").toHaveCount(0);
    expect(".o_field_many2one[name=product_id] .o_m2o_no_result").toHaveCount(1);
    await contains(getFixture()).click();
    expect(".o_field_many2one[name=product_id] .o_m2o_no_result").toHaveCount(0);
});

test("pressing enter in a m2o in an editable list", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="product_id" />
            </list>`,
    });

    await contains("td.o_data_cell").click();
    expect(".o_selected_row").toHaveCount(1);

    // we now write 'a' and press enter to check that the selection is
    // working, and prevent the navigation
    await contains("[name=product_id] input").edit("a", { confirm: false });
    await runAllTimers();
    expect("[name=product_id] .o-autocomplete--dropdown-menu").toHaveCount(1);

    // we now trigger ENTER to select first choice
    await press("Enter");
    await animationFrame();

    expect("[name=product_id] input").toBeFocused();
    expect("[name=product_id] .o-autocomplete--dropdown-menu").toHaveCount(0);

    // we now trigger again ENTER to make sure we can move to next line
    await press("Enter");
    await animationFrame();

    expect("tr.o_data_row:nth-child(1) [name=product_id] input").toHaveCount(0);
    expect("tr.o_data_row:nth-child(2)").toHaveClass("o_selected_row");

    // we now write again 'a' in the cell to select xpad. We will now
    // test with the tab key
    await contains("[name=product_id] input").edit("a", { confirm: false });
    await runAllTimers();
    expect(
        "tr.o_data_row:nth-child(2) [name=product_id] .o-autocomplete--dropdown-menu"
    ).toHaveCount(1);

    await press("Tab");
    await animationFrame();

    expect("tr.o_data_row:nth-child(2) [name=product_id] input").toHaveCount(0);

    expect("tr.o_data_row:nth-child(3)").toHaveClass("o_selected_row");
});

test("pressing ENTER on a 'no_quick_create' many2one should open a M2ODialog", async () => {
    Partner._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu" options="{'no_quick_create': 1}" />
                <field name="foo" />
            </form>`,
    });

    await contains(".o_field_many2one input").edit("Something that does not exist", {
        confirm: false,
    });
    await runAllTimers();
    await press("Enter");
    await animationFrame();
    expect(".modal").toHaveCount(1);
    // Check that discarding clears $input
    await contains(".modal .o_form_button_cancel").click();
    expect(".o_field_many2one input").toHaveValue("");
});

test("select a value by pressing TAB on a many2one with onchange", async () => {
    Partner._onChanges = {
        trululu: () => {},
    };

    const def = new Deferred();

    onRpc("onchange", () => def);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="trululu" />
                <field name="name" />
            </form>`,
    });

    await contains(".o_field_many2one input").edit("first", { confirm: "tab" });

    // simulate a focusout (e.g. because the user clicks outside)
    // before the onchange returns
    await click(".o_field_char");

    expect(".modal").toHaveCount(0);

    // unlock the onchange
    def.resolve();
    await runAllTimers();

    expect(".o_field_many2one input").toHaveValue("first record");
    expect(".modal").toHaveCount(0);
});

test("leaving a many2one by pressing tab", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu"/>
                <field name="name"/>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    await runAllTimers();
    await press("tab");
    await animationFrame();

    expect(".o_field_many2one input").toHaveValue("");

    // open autocomplete dropdown and manually select item by UP/DOWN key and press TAB
    await contains(".o_field_many2one input").click();
    await runAllTimers();
    await press("arrowdown");
    await press("tab");
    await animationFrame();

    expect(".o_field_many2one input").toHaveValue("second record");

    // clear many2one and then open autocomplete, write something and press TAB
    await contains(".o_field_many2one input").edit("", { confirm: false });
    await runAllTimers();
    await contains(".o_field_many2one input").click();
    await contains(".o_field_many2one input").edit("se", { confirm: "tab" });
    await runAllTimers();

    expect(".o_field_many2one input").toHaveValue("second record");
});

test("leaving an empty many2one by pressing tab (after backspace or delete)", async () => {
    expect.assertions(4);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="trululu"/>
                <field name="name"/>
            </form>`,
    });

    expect(".o_field_many2one input").toHaveValue();

    // simulate backspace to remove values and press TAB
    await contains(".o_field_many2one input").edit("", { confirm: false });
    await runAllTimers();
    await press("backspace");
    await press("tab");
    await animationFrame();
    expect(".o_field_many2one input").toHaveValue("");

    // reset a value
    await selectFieldDropdownItem("trululu", "first record");
    expect(".o_field_many2one input").toHaveValue("first record");

    // simulate delete to remove values and press TAB
    await contains(".o_field_many2one input").edit("", { confirm: false });
    await runAllTimers();
    await press("delete");
    await press("tab");
    // TODO: fix owl
    await animationFrame();
    expect(".o_field_many2one input").toHaveValue("");
});

test("many2one in editable list + onchange, with enter", async () => {
    Partner._onChanges = {
        product_id: (obj) => {
            obj.int_field = obj.product_id || 0;
        },
    };

    const def = new Deferred();

    onRpc("onchange", () => def);
    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="product_id" />
                <field name="int_field" />
            </list>`,
    });

    await contains("td.o_data_cell").click();
    await contains("td.o_data_cell input").edit("a", { confirm: false });
    await runAllTimers();
    await press("enter");
    def.resolve();
    await animationFrame();
    await press("enter");
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect.verifySteps([
        "get_views",
        "web_search_read", // to display results in the dialog
        "has_group",
        "web_name_search",
        "onchange",
        "web_save",
    ]);
});

test("many2one in editable list + onchange, with enter, part 2", async () => {
    // this is the same test as the previous one, but the onchange is just
    // resolved slightly later
    Partner._onChanges = {
        product_id: (obj) => {
            obj.int_field = obj.product_id || 0;
        },
    };

    const def = new Deferred();
    onRpc("onchange", () => def);
    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
                <list editable="bottom">
                    <field name="product_id" />
                    <field name="int_field" />
                </list>`,
    });

    await contains("td.o_data_cell").click();
    await contains("td.o_data_cell input").edit("a", { confirm: false });
    await runAllTimers();
    await press("enter");
    await press("enter");
    def.resolve();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect.verifySteps([
        "get_views",
        "web_search_read", // to display results in the dialog
        "has_group",
        "web_name_search",
        "onchange",
        "web_save",
    ]);
});

test("many2one: dynamic domain set in the field's definition", async () => {
    expect.assertions(2);
    Partner._fields.trululu = fields.Many2one({
        string: "Trululu",
        relation: "partner",
        domain: "[('foo' ,'=', foo)]",
    });
    onRpc("web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["foo", "=", "yop"]]);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="foo" invisible="1" />
                <field name="trululu" />
            </list>`,
    });

    await contains(".o_data_cell:eq(0)").click();
    await contains(".o_field_many2one input").click();

    expect(".o_field_many2one .o-autocomplete--dropdown-item").toHaveCount(2);
});

test("many2one: domain set in view and on field", async () => {
    expect.assertions(2);
    Partner._fields.trululu = fields.Many2one({
        string: "Trululu",
        relation: "partner",
        domain: "[('foo' ,'=', 'boum')]",
    });
    onRpc("web_name_search", ({ kwargs }) => {
        // should only use the domain set in the view
        expect(kwargs.domain).toEqual([["foo", "=", "blip"]]);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="foo" invisible="1"/>
                <field name="trululu" domain="[['foo', '=', 'blip']]"/>
            </list>`,
    });

    await contains(".o_data_cell:eq(0)").click();
    await contains(".o_field_many2one input").click();

    expect(".o_field_many2one .o-autocomplete--dropdown-item").toHaveCount(2);
});

test("many2one: domain updated by an onchange", async () => {
    expect.assertions(2);
    Partner._onChanges = {
        int_field: () => {},
    };

    let domain = [];
    onRpc("onchange", () => {
        domain = [["id", "in", [10]]];
        return {
            domain: {
                trululu: domain,
                unexisting_field: domain,
            },
        };
    });
    onRpc("web_name_search", ({ kwargs }) => {
        expect(kwargs.domain).toEqual(domain);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="int_field" />
                <field name="trululu" />
            </form>`,
    });

    // trigger a web_name_search (domain should be [])
    await contains(".o_field_widget[name=trululu] input").click();
    // close the dropdown
    await contains(".o_field_widget[name=trululu] input").click();
    // trigger an onchange that will update the domain

    // trigger a web_name_search (domain should be [['id', 'in', [10]]])
    await contains(".o_field_widget[name='trululu'] input").click();
});

test("search more in many2one: no text in input", async () => {
    // when the user clicks on 'Search more...' in a many2one dropdown, and there is no text
    // in the input (i.e. no value to search on), we bypass the web_name_search that is meant to
    // return a list of preselected ids to filter on in the list view (opened in a dialog)
    expect.assertions(2);

    for (let i = 0; i < 8; i++) {
        Partner._records.push({ id: 100 + i, name: `test_${i}` });
    }
    Partner._views = {
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    onRpc(({ method }) => {
        expect.step(method);
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    await contains(`.o_field_widget[name="trululu"] input`).clear();

    await contains(`.o_field_widget[name="trululu"] input`).click();
    await contains(`.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`).click();

    expect.verifySteps([
        "get_views", // main form view
        "onchange",
        "web_name_search", // to display results in the dropdown
        "get_views", // list view in dialog
        "has_group",
        "web_search_read", // to display results in the dialog
    ]);
});

test("search more in many2one: text in input", async () => {
    // when the user clicks on 'Search more...' in a many2one dropdown, and there is some
    // text in the input, we perform a web_name_search to get a (limited) list of preselected
    // ids and we add a dynamic filter (with those ids) to the search view in the dialog, so
    // that the user can remove this filter to bypass the limit
    expect.assertions(5);

    for (let i = 0; i < 8; i++) {
        Partner._records.push({ id: 100 + i, name: `test_${i}` });
    }
    Partner._views = {
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    let expectedDomain;
    onRpc(({ method }) => {
        expect.step(method);
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual(expectedDomain);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    expectedDomain = [["id", "in", [100, 101, 102, 103, 104, 105, 106, 107]]];
    await contains(`.o_field_widget[name="trululu"] input`).click();

    await contains(".o_field_widget[name='trululu'] input").edit("test", { confirm: false });
    await runAllTimers();
    await contains(`.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`).click();

    expect(".modal .o_list_view").toHaveCount(1);
    expect(".modal .o_cp_searchview .o_facet_values").toHaveCount(1);

    // remove the filter on ids
    expectedDomain = [];
    await contains(".modal .o_cp_searchview .o_facet_remove").click();

    expect.verifySteps([
        "get_views", // main form view
        "onchange",
        "web_name_search", // empty search, triggered when the user clicks in the input
        "web_name_search", // to display results in the dropdown
        "name_search", // to get preselected ids matching the search
        "get_views", // list view in dialog
        "has_group",
        "web_search_read", // to display results in the dialog
        "web_search_read", // after removal of dynamic filter
    ]);
});

test("search more in many2one: dropdown click", async () => {
    for (let i = 0; i < 8; i++) {
        Partner._records.push({ id: 100 + i, name: `test_${i}` });
    }
    Partner._views = {
        list: `
            <list>
                <field name="name" />
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    await contains(`.o_field_widget[name="trululu"] input`).click();

    await contains(".o_field_widget[name='trululu'] input").edit("test", { confirm: false });
    await runAllTimers();
    await contains(`.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`).click();

    // dropdown selector
    const searchDropdown = ".o_control_panel_actions .o-dropdown";
    await contains(searchDropdown).click();
    expect(searchDropdown).toHaveClass("show");
    expect(getDropdownMenu(searchDropdown)).toBeVisible();
});

test("updating a many2one from a many2many", async () => {
    expect.assertions(5);

    Turtle._records[1].turtle_trululu = 1;
    Partner._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    onRpc("get_formview_id", ({ args }) => {
        expect(args[0]).toEqual([1]);
        return false;
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        viewId: 1,
        arch: `
            <form>
                <field name="turtles">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="turtle_trululu"/>
                    </list>
                </field>
            </form>`,
    });
    expect(".modal").toHaveCount(1);

    // Opening the modal
    await contains(".o_data_row td:eq(1)").click();
    await contains(".o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);

    // Changing the 'trululu' value
    await contains(".o_dialog:not(.o_inactive_modal) div[name=name] input").edit("test");
    await contains(".modal:eq(1) .o_form_button_save").click();

    expect(".modal").toHaveCount(1);

    // Test whether the value has changed
    expect(".o_dialog:not(.o_inactive_modal) div[name=turtle_trululu] input").toHaveValue("test");
});

test("search more in many2one: cannot resequence inside dialog", async () => {
    // when the user clicks on 'Search more...' in a many2one dropdown, resequencing inside
    // the dialog works
    Partner._fields.sequence = fields.Integer();
    for (let i = 0; i < 8; i++) {
        Partner._records.push({ id: 100 + i, name: `test_${i}` });
    }
    Partner._views = {
        list: `
            <list>
                <field name="sequence" widget="handle" />
                <field name="name" />
            </list>`,
    };

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([]);
    });
    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" /></form>',
    });

    await contains(".o_field_widget[name='trululu'] input").click();
    await runAllTimers();
    await contains(`.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`).click();

    expect(".modal").toHaveCount(1);
    expect(".modal .o_row_handle.o_disabled").toHaveCount(11);

    expect.verifySteps([
        "get_views",
        "onchange",
        "web_name_search", // to display results in the dropdown
        "get_views", // list view in dialog
        "web_search_read", // to display results in the dialog
        "has_group",
    ]);
});

test("many2one dropdown disappears on scroll", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <div style="height: 2000px;">
                    <field name="trululu" />
                </div>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".o_field_many2one .dropdown-menu").toHaveCount(1);

    const dropdown = queryOne(".o_field_many2one .dropdown-menu");
    dropdown.style = "max-height: 40px;";

    await scroll(dropdown, { top: 50 });

    expect(dropdown).toHaveProperty("scrollTop", 50);
    expect(".o_field_many2one .dropdown-menu").toHaveCount(1);

    await scroll(".o_content", { top: 50 });
    await animationFrame();

    expect(".o_field_many2one .dropdown-menu").toHaveCount(0);
});

test("search more in many2one: group and use the pager", async () => {
    Partner._records.push(
        {
            id: 5,
            name: "Partner 4",
        },
        {
            id: 6,
            name: "Partner 5",
        },
        {
            id: 7,
            name: "Partner 6",
        },
        {
            id: 8,
            name: "Partner 7",
        },
        {
            id: 9,
            name: "Partner 8",
        },
        {
            id: 10,
            name: "Partner 9",
        }
    );

    Partner._views = {
        list: `
            <list limit="7">
                <field name="name" />
            </list>`,
        search: `
            <search><group>
                <filter name="bar" string="Bar" context="{'group_by': 'bar'}" />
            </group></search>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="trululu" /></form>',
    });

    await selectFieldDropdownItem("trululu", "Search more...");
    await toggleSearchBarMenu(".modal");
    await toggleMenuItem("Bar");

    await contains(".modal .o_group_header:eq(1)").click();

    expect(".modal .o_data_row").toHaveCount(7);
    await contains(".modal .o_group_header .o_pager_next").click();
    expect(".modal .o_data_row").toHaveCount(1);
});

test("focus when closing many2one modal in many2one modal", async () => {
    Partner._views = {
        form: '<form><field name="trululu"/></form>',
    };

    onRpc("get_formview_id", () => false);

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 2,
    });

    expect(".o_dialog").toHaveCount(1);
    expect(document.body).toHaveClass("modal-open");

    // Open many2one modal
    await contains(".o_external_button", { visible: false }).click();

    const originalModal = queryOne(".o_dialog:eq(1)");

    expect(".o_dialog").toHaveCount(2);
    expect(originalModal).not.toHaveClass("o_inactive_modal");
    expect(document.body).toHaveClass("modal-open");

    // Open many2one modal of field in many2one modal
    await contains(".o_dialog:eq(1) .o_external_button", { visible: false }).click();

    expect(".o_dialog").toHaveCount(3);
    expect(".o_dialog:eq(2)").not.toHaveClass("o_inactive_modal");
    expect(document.body).toHaveClass("modal-open");

    // Close second modal
    await contains(".o_dialog:eq(2) button[class='btn-close']").click();

    expect(".o_dialog").toHaveCount(2);
    expect(originalModal).toBe(queryOne(".o_dialog:eq(1)"), {
        message: "First modal is still opened",
    });
    expect(".o_dialog:eq(1)").not.toHaveClass("o_inactive_modal");
    expect(document.body).toHaveClass("modal-open");

    // Close first modal
    await contains(".o_dialog:eq(1) button[class='btn-close']").click();
    expect(".o_dialog").toHaveCount(1);
});

test("search more pager is reset when doing a new search", async () => {
    Partner._fields.datetime = fields.Datetime({ string: "Datetime Field", searchable: true });
    Partner._records.push(
        ...new Array(170).fill().map((_, i) => ({ id: i + 10, name: "Partner " + i }))
    );
    Partner._views = {
        list: `
            <list>
                <field name="name"/>
            </list>`,
        search: `
            <search>
                <field name="datetime"/>
                <field name="name"/>
            </search>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="trululu"/>
                    </group>
                </sheet>
            </form>`,
    });

    await selectFieldDropdownItem("trululu", "Search more...");

    await contains(".modal .o_pager_next").click();

    expect(".modal .o_pager_limit").toHaveText("173");
    expect(".modal .o_pager_value").toHaveText("81-160");
    expect(".modal tr.o_data_row").toHaveCount(80);

    await editSearch("first");
    await validateSearch();

    expect(".modal .o_pager_limit").toHaveText("1");
    expect(".modal .o_pager_value").toHaveText("1-1");
    expect(".modal tr.o_data_row").toHaveCount(1);
});

test("click on many2one link in list view", async () => {
    Turtle._records[1].product_id = 37;
    Partner._views = {
        form: '<form> <field name="turtles"/> </form>',
    };
    Turtle._views = {
        list: `
            <list readonly="1">
                <field name="product_id" widget="many2one" context="{'field': 'Yes'}"/>
            </list>`,
    };
    onRpc("get_formview_action", (args) => {
        expect.step("get_formview_action");
        expect(args.kwargs.context.field).toBe("Yes");
        expect(args.kwargs.context).not.toInclude("global");
        return {
            type: "ir.actions.act_window",
            res_model: "product",
            view_type: "form",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            res_id: args[0],
        };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        res_id: 1,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        context: { global: "No" },
    });
    expect("a.o_form_uri").toHaveCount(1);
    expect(".o_breadcrumb").toHaveCount(1);

    await contains("a.o_form_uri").click();
    expect.verifySteps(["get_formview_action"]);
    expect(".breadcrumb-item").toHaveCount(1);
    expect(".o_breadcrumb").toHaveCount(1);
});

test("Many2oneField with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu" placeholder="Placeholder"/></form>',
    });

    expect(".o_field_widget[name='trululu'] input").toHaveAttribute("placeholder", "Placeholder");
});

test("placeholder_field shows as placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <field name="name"/>
            <field name="trululu" options="{'placeholder_field': 'name'}"/>
        </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name='trululu'] input").toHaveAttribute("placeholder", "first record");
});

test("external_button performs a doAction by default", async () => {
    Partner._views = {
        form: '<form><field name="trululu"/></form>',
    };
    onRpc("get_formview_action", () => {
        expect.step("get_formview_action");
        return {
            type: "ir.actions.act_window",
            res_model: "partner",
            view_type: "form",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            res_id: false,
        };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        res_id: 1,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    await selectFieldDropdownItem("trululu", "first record");
    expect(".o_field_widget .o_external_button .oi-arrow-right").toHaveCount(1);
    await contains(".o_field_widget .o_external_button", { visible: false }).click();

    expect.verifySteps(["get_formview_action"]);
    expect(".breadcrumb").toHaveText("first record");
});

test("external_button opens a FormViewDialog in dialogs", async () => {
    onRpc("get_formview_id", () => {
        expect.step("get_formview_id");
        return false;
    });
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu"/></form>',
    });
    expect(".modal").toHaveCount(1);

    await selectFieldDropdownItem("trululu", "first record");
    expect(".o_field_widget .o_external_button .oi-launch").toHaveCount(1);
    await contains(".o_field_widget .o_external_button", { visible: false }).click();

    expect.verifySteps(["get_formview_id"]);
    expect(".modal").toHaveCount(2);
});

test("external_button opens a new tab when middle clicked or ctrl+click", async () => {
    mockService("action", {
        doAction(params, options) {
            if (options?.newWindow) {
                expect.step("opened in a new window");
                return;
            }
            super.doAction(params);
        },
        loadState() {},
    });
    Partner._views = {
        form: '<form><field name="trululu"/></form>',
    };
    onRpc("get_formview_action", () => ({
        type: "ir.actions.act_window",
        res_model: "partner",
        view_type: "form",
        view_mode: "form",
        views: [[false, "form"]],
        target: "current",
        res_id: false,
    }));
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        res_id: 1,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    await selectFieldDropdownItem("trululu", "first record");
    await contains(".o_external_button", { visible: false }).click({ ctrlKey: true });
    expect.verifySteps(["opened in a new window"]);
    await middleClick(".o_external_button");
    await animationFrame();
    expect.verifySteps(["opened in a new window"]);
});

test("keep changes when editing related record in a dialog", async () => {
    Partner._views = {
        [["form", 98]]: '<form><field name="int_field"/></form>',
    };
    onRpc("get_formview_id", () => 98);
    onRpc("web_save", () => {
        expect.step("web_save");
    });
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="foo"/><field name="trululu"/></form>',
    });
    expect(".modal").toHaveCount(1);

    await contains(".o_field_widget[name=foo] input").edit("some value", { confirm: false });
    await runAllTimers();
    await selectFieldDropdownItem("trululu", "first record");
    expect(".o_field_widget .o_external_button .oi-launch").toHaveCount(1);
    await contains(".o_field_widget .o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);

    await contains(".o_dialog:not(.o_inactive_modal) .o_field_widget[name=int_field] input").edit(
        "5464"
    );
    await contains(
        ".o_dialog:not(.o_inactive_modal) .modal-footer .btn-primary:not(.d-none)"
    ).click();

    expect(".modal").toHaveCount(1);
    expect(".o_field_widget[name=foo] input").toHaveValue("some value");
    expect.verifySteps(["web_save"]);
});

test("create and edit, save and then discard", async () => {
    Partner.views = {
        [[98, "form"]]: '<form><field name="name"/></form>',
    };
    onRpc("get_formview_id", () => 98);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="trululu"/></form>',
        resId: 1,
    });

    expect(".o_field_widget[name=trululu] input").toHaveValue("aaa");

    await contains(".o_field_widget[name=trululu] input").edit("new m2o", { confirm: false });
    await runAllTimers();
    await contains(".o_field_widget[name=trululu] input").click();
    await selectFieldDropdownItem("trululu", "Create and edit...");
    expect(".modal").toHaveCount(1);

    await contains(".modal-footer .btn-primary:not(.d-none)").click();
    expect(".modal").toHaveCount(0);
    expect(".o_field_widget[name=trululu] input").toHaveValue("new m2o");

    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=trululu] input").toHaveValue("aaa");
});

test("external button must be displayed after the update caused by an onchange", async () => {
    Partner._onChanges = {
        name: (obj) => {
            if (obj.name) {
                obj.trululu = 1;
            }
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name"/>
                <field name="trululu"/>
            </form>`,
    });

    expect(".o_external_button").toHaveCount(0);

    await contains("[name=name] input").edit("new value");
    expect(".o_external_button").toHaveCount(1);
});

test("many2one field with false as name", async () => {
    Partner._records[0].name = false;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="trululu"/>
            </form>`,
    });

    expect(".o_field_widget[name='trululu'] input").toHaveValue("Unnamed");
});

test("many2one search with false as name", async () => {
    onRpc("web_name_search", () => [
        { id: 1, display_name: false, __formatted_display_name: false },
    ]);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu" />
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".o_field_many2one[name='trululu'] .dropdown-menu a.dropdown-item:eq(0)").toHaveText(
        "Unnamed"
    );
});

test("many2one search with formatted name", async () => {
    onRpc("web_name_search", () => [
        {
            id: 1,
            display_name: "Paul Eric",
            __formatted_display_name: "Test: **Paul** --Eric-- `good guy`\n\tMore text",
        },
    ]);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="trululu" />
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(
        ".o_field_many2one[name='trululu'] .dropdown-menu a.dropdown-item:eq(0)"
    ).toHaveInnerHTML(
        `Test: <b>Paul</b> <span class="text-muted">Eric</span> <span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">good guy</span><br/><span style="margin-left: 2em"></span>More text`
    );
    await contains(
        ".o_field_many2one[name='trululu'] .dropdown-menu a.dropdown-item:eq(0)"
    ).click();
    expect(".o_field_many2one input").toHaveValue("Paul Eric");
});

test.tags("desktop");
test("search typeahead", async () => {
    onRpc("web_name_search", () => expect.step("web_name_search"));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="trululu" options="{ 'search_threshold': 3 }"/></form>`,
    });

    await contains(".o_field_widget[name=trululu] input").click();
    await runAllTimers();
    expect.verifySteps([]);
    expect(queryAllTexts(`.o-autocomplete.dropdown li`)).toEqual([
        "Start typing 3 characters",
        "Search more...",
    ]);

    await contains(".o_field_widget[name=trululu] input").edit("r", { confirm: false });
    await runAllTimers();
    expect.verifySteps([]);
    expect(queryAllTexts(`.o-autocomplete.dropdown li`)).toEqual([
        "Start typing 3 characters",
        'Create "r"',
        "Create and edit...",
        "Search more...",
    ]);

    await contains(".o_field_widget[name=trululu] input").edit("re", { confirm: false });
    await runAllTimers();
    expect.verifySteps([]);
    expect(queryAllTexts(`.o-autocomplete.dropdown li`)).toEqual([
        "Start typing 3 characters",
        'Create "re"',
        "Create and edit...",
        "Search more...",
    ]);

    await contains(".o_field_widget[name=trululu] input").edit("rec", { confirm: false });
    await runAllTimers();
    expect.verifySteps(["web_name_search"]);
    expect(queryAllTexts(`.o-autocomplete.dropdown li`)).toEqual([
        "first record",
        "second record",
        'Create "rec"',
        "Create and edit...",
        "Search more...",
    ]);
});

test("highlight search in many2one", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="trululu"/></form>`,
    });
    await contains(".o_field_widget[name=trululu] input").edit("rec", { confirm: false });
    await runAllTimers();
    expect(`.o-autocomplete.dropdown li:not(.o_m2o_dropdown_option) a`).toHaveCount(2);
    expect(`.o-autocomplete.dropdown li:eq(0) a`).toHaveInnerHTML(`
        first
        <span class="text-primary fw-bold">
            rec
        </span>
        ord
    `);
    expect(`.o-autocomplete.dropdown li:eq(1) a`).toHaveInnerHTML(`
        second
        <span class="text-primary fw-bold">
            rec
        </span>
        ord
    `);
});
