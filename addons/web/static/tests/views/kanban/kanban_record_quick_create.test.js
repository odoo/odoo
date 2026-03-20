import { beforeEach, expect, test } from "@odoo/hoot";
import {
    click,
    drag,
    edit,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    resize,
    unload,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockSendBeacon, runAllTimers } from "@odoo/hoot-mock";
import {
    clickModalButton,
    contains,
    createKanbanRecord,
    defineModels,
    discardKanbanRecord,
    editKanbanColumnName,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    fields,
    getKanbanColumn,
    getKanbanRecord,
    getKanbanRecordTexts,
    getService,
    hideTab,
    makeServerError,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    quickCreateKanbanColumn,
    quickCreateKanbanRecord,
    stepAllNetworkCalls,
    toggleKanbanColumnActions,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
    validateKanbanColumn,
    validateKanbanRecord,
    webModels,
} from "@web/../tests/web_test_helpers";

import { AnimatedNumber } from "@web/views/view_components/animated_number";
import { WebClient } from "@web/webclient/webclient";

const { IrAttachment } = webModels;

class Partner extends models.Model {
    _name = "partner";
    _rec_name = "foo";

    foo = fields.Char();
    bar = fields.Boolean();
    sequence = fields.Integer();
    int_field = fields.Integer({ aggregator: "sum", sortable: true });
    float_field = fields.Float({ aggregator: "sum" });
    product_id = fields.Many2one({ relation: "product" });
    category_ids = fields.Many2many({ relation: "category" });
    date = fields.Date();
    datetime = fields.Datetime();
    state = fields.Selection({
        type: "selection",
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });
    salary = fields.Monetary({ aggregator: "sum", currency_field: "currency_id" });
    currency_id = fields.Many2one({ relation: "res.currency" });

    _records = [
        {
            id: 1,
            foo: "yop",
            bar: true,
            int_field: 10,
            float_field: 0.4,
            product_id: 3,
            category_ids: [],
            state: "abc",
            salary: 1750,
            currency_id: 1,
        },
        {
            id: 2,
            foo: "blip",
            bar: true,
            int_field: 9,
            float_field: 13,
            product_id: 5,
            category_ids: [6],
            state: "def",
            salary: 1500,
            currency_id: 1,
        },
        {
            id: 3,
            foo: "gnap",
            bar: true,
            int_field: 17,
            float_field: -3,
            product_id: 3,
            category_ids: [7],
            state: "ghi",
            salary: 2000,
            currency_id: 2,
        },
        {
            id: 4,
            foo: "blip",
            bar: false,
            int_field: -4,
            float_field: 9,
            product_id: 5,
            category_ids: [],
            state: "ghi",
            salary: 2222,
            currency_id: 1,
        },
    ];
}

class Product extends models.Model {
    _name = "product";

    name = fields.Char();
    fold = fields.Boolean({ default: false });

    _records = [
        { id: 3, name: "hello" },
        { id: 5, name: "xmo" },
    ];
}

class Category extends models.Model {
    _name = "category";

    name = fields.Char();
    color = fields.Integer();

    _records = [
        { id: 6, name: "gold", color: 2 },
        { id: 7, name: "silver", color: 5 },
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
    inverse_rate = fields.Float();

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before", inverse_rate: 1 },
        { id: 2, name: "EUR", symbol: "€", position: "after", inverse_rate: 0.5 },
    ];
}

class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}

defineModels([Partner, Product, Category, Currency, IrAttachment, User]);

beforeEach(() => {
    patchWithCleanup(AnimatedNumber, { enableAnimations: false });
});

test.tags("desktop");
test("create in grouped on m2o", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group.o_group_draggable").toHaveCount(2);
    expect(".o_control_panel_main_buttons button.o-kanban-button-new").toHaveCount(1);
    expect(".o_column_quick_create").toHaveCount(0, {
        message: "no quick create since no default groupby",
    });

    await createKanbanRecord();

    expect(".o_kanban_group:first-child > .o_kanban_quick_create").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(2)", "xmo\n(2)"]);
});

test("create in grouped on char", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    expect(".o_kanban_group.o_group_draggable").toHaveCount(0);
    expect(".o_kanban_group").toHaveCount(3);
    expect(queryAllTexts(".o_column_title")).toEqual(["blip\n(2)", "gnap\n(1)", "yop\n(1)"]);
    expect(".o_kanban_group:first-child > .o_kanban_quick_create").toHaveCount(0);
});

test.tags("desktop");
test("quick created records in grouped kanban are on displayed top", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);

    await createKanbanRecord();

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await edit("new record");
    await validateKanbanRecord();

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    // the new record must be the first record of the column
    expect(queryAllTexts(" .o_kanban_group:first .o_kanban_record")).toEqual([
        "new record",
        "yop",
        "gnap",
    ]);

    await click(".o_kanban_quick_create input"); // FIXME: should not be necessary
    await edit("another record");
    await validateKanbanRecord();

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(4);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(queryAllTexts(".o_kanban_group:first .o_kanban_record")).toEqual([
        "another record",
        "new record",
        "yop",
        "gnap",
    ]);
});

test.tags("desktop");
test("quick create record without quick_create_view", async () => {
    stepAllNetworkCalls();
    onRpc("name_create", ({ args }) => {
        expect(args[0]).toBe("new partner");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);

    // click on 'Create' -> should open the quick create in the first column
    await createKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create .o_form_view.o_xxs_form_view").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveCount(1);
    expect(
        ".o_kanban_quick_create .o_field_widget.o_required_modifier input[placeholder=Title]"
    ).toHaveCount(1);

    // fill the quick create and validate
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test.tags("desktop");
test("quick create record with quick_create_view", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
            <field name="state" widget="priority"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            foo: "new partner",
            int_field: 4,
            state: "def",
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_control_panel").toHaveCount(1);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);

    // click on 'Create' -> should open the quick create in the first column
    await createKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create .o_form_view.o_xxs_form_view").toHaveCount(1);
    expect(".o_control_panel").toHaveCount(1, {
        message: "should not have instantiated another control panel",
    });
    expect(".o_kanban_quick_create input").toHaveCount(2);
    expect(".o_kanban_quick_create .o_field_widget").toHaveCount(3);

    // fill the quick create and validate
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await editKanbanRecordQuickCreateInput("int_field", "4");
    await click(".o_kanban_quick_create .o_field_widget[name=state] .o_priority_star:first-child");
    await validateKanbanRecord();
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "get_views", // form view in quick create
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "onchange", // new quick create
        "web_read", // read the created record
    ]);
});

test.tags("desktop");
test("quick create record flickering", async () => {
    let def;
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
            <field name="state" widget="priority"/>
        </form>`;

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            foo: "new partner",
            int_field: 4,
            state: "def",
        });
    });
    onRpc("onchange", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // click on 'Create' -> should open the quick create in the first column
    await createKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create .o_form_view.o_xxs_form_view").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveCount(2);
    expect(".o_kanban_quick_create .o_field_widget").toHaveCount(3);

    // fill the quick create and validate
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await editKanbanRecordQuickCreateInput("int_field", "4");

    await click(".o_kanban_quick_create .o_field_widget[name=state] .o_priority_star:first-child");
    def = new Deferred();
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);

    def.resolve();
    await animationFrame();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
});

test.tags("desktop");
test("quick create record flickering (load more)", async () => {
    let def;
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    onRpc("read", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // click on 'Create' -> should open the quick create in the first column
    await createKanbanRecord();

    // fill the quick create and validate
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    def = new Deferred();
    await validateKanbanRecord();
    expect(".o_kanban_load_more").toHaveCount(0);
    def.resolve();
    await animationFrame();
    expect(".o_kanban_load_more").toHaveCount(0);
});

test.tags("desktop");
test("quick create record should focus default field", async function () {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field" default_focus="1"/>
            <field name="state" widget="priority"/>
        </form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await createKanbanRecord();

    expect(".o_field_widget[name=int_field] input:first").toBeFocused();
});

test.tags("desktop");
test("quick create record should focus first field input", async function () {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
            <field name="state" widget="priority"/>
        </form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await createKanbanRecord();
    expect(".o_field_widget[name=foo] input:first").toBeFocused();

    await editKanbanRecordQuickCreateInput("foo", "test");
    await contains(".o_kanban_quick_create .o_kanban_add").click();
    expect(".o_field_widget[name=foo] input:first").toHaveValue("");
    expect(".o_field_widget[name=foo] input:first").toBeFocused();
});

test.tags("desktop");
test("quick_create_view without quick_create option", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="display_name"/>
        </form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        createRecord() {
            expect.step("create record");
        },
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group .o_kanban_quick_add").toHaveCount(2);

    // click on 'Create' in control panel -> should not open the quick create
    await createKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(0);
    expect.verifySteps(["create record"]);

    // click "+" icon in first column -> should open the quick create
    await contains(".o_kanban_quick_add").click();
    await animationFrame();
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect.verifySteps([]);
});

test.tags("desktop");
test("quick create record in grouped on m2o (no quick_create_view)", async () => {
    expect.assertions(6);

    stepAllNetworkCalls();
    onRpc("name_create", ({ args, kwargs }) => {
        expect(args[0]).toBe("new partner");
        const { default_product_id, default_float_field } = kwargs.context;
        expect(default_product_id).toBe(3);
        expect(default_float_field).toBe(2.5);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        context: { default_float_field: 2.5 },
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    // click on 'Create', fill the quick create and validate
    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test.tags("desktop");
test("quick create record in grouped on m2o (with quick_create_view)", async () => {
    expect.assertions(6);

    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
            <field name="state" widget="priority"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("web_save", ({ method, args, kwargs }) => {
        expect(args[1]).toEqual({
            foo: "new partner",
            int_field: 4,
            state: "def",
        });
        const { default_product_id, default_float_field } = kwargs.context;
        expect(default_product_id).toBe(3);
        expect(default_float_field).toBe(2.5);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        context: { default_float_field: 2.5 },
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    // click on 'Create', fill the quick create and validate
    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await animationFrame();
    await editKanbanRecordQuickCreateInput("int_field", 4);
    await animationFrame();
    await contains(
        ".o_kanban_quick_create .o_field_widget[name=state] .o_priority_star:first-child"
    ).click();
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "get_views", // form view in quick create
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test("quick create record in grouped on m2m (no quick_create_view)", async () => {
    stepAllNetworkCalls();
    onRpc("name_create", ({ args, kwargs }) => {
        expect(args[0]).toBe("new partner");
        expect(kwargs.context.default_category_ids).toEqual([6]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["category_ids"],
    });

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);

    // click on 'Create', fill the quick create and validate
    await quickCreateKanbanRecord(1);
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await animationFrame();
    await validateKanbanRecord();

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test.tags("desktop");
test("quick create record in grouped on m2m in the None column", async () => {
    stepAllNetworkCalls();
    onRpc("name_create", ({ args, kwargs }) => {
        expect(args[0]).toBe("new partner");
        expect(kwargs.context.default_category_ids).toBe(false);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["category_ids"],
    });

    await contains(".o_kanban_group:nth-child(1)").click();

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(2);

    // click on 'Create', fill the quick create and validate
    await quickCreateKanbanRecord(0);
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await animationFrame();
    await validateKanbanRecord();

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(3);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "web_search_read", // read records when unfolding 'None'
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test("quick create record in grouped on m2m (field not in template)", async () => {
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ foo: "new partner" });
        expect(kwargs.context.default_category_ids).toEqual([6]);
        return [{ id: 5 }];
    });
    onRpc("web_read", ({ args }) => {
        if (args[0][0] === 5) {
            return [{ id: 5, foo: "new partner", category_ids: [6] }];
        }
    });
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["category_ids"],
    });

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);

    // click on 'Create', fill the quick create and validate
    await quickCreateKanbanRecord(1);
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "get_views", // get form view
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "onchange", // reopen the quick create automatically
        "web_read", // read the created record
    ]);
});

test("quick create record in grouped on m2m (field in the form view)", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="category_ids" widget="many2many_tags"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("web_save", ({ method, args, kwargs }) => {
        expect(args[1]).toEqual({
            category_ids: [[4, 6]],
            foo: "new partner",
        });
        expect(kwargs.context.default_category_ids).toEqual([6]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["category_ids"],
    });

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);

    // click on 'Create', fill the quick create and validate
    await quickCreateKanbanRecord(1);

    // verify that the quick create m2m field contains the column value
    expect(".o_tag_badge_text").toHaveCount(1);
    expect(".o_tag_badge_text").toHaveText("gold");

    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "get_views", // get form view
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "onchange",
        "web_read",
    ]);
});

test.tags("desktop");
test("quick create record validation: stays open when invalid", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
    ]);

    await createKanbanRecord();
    expect.verifySteps(["onchange"]);

    // do not fill anything and validate
    await validateKanbanRecord();

    expect.verifySteps([]);
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect("[name=display_name]").toHaveClass("o_field_invalid");
    expect(".o_notification_manager .o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText("Invalid Display Name");
});

test.tags("desktop");
test("quick create record with default values and onchanges", async () => {
    Partner._fields.int_field = fields.Integer({ default: 4 });
    Partner._fields.foo = fields.Char({
        onChange: (obj) => {
            if (obj.foo) {
                obj.int_field = 8;
            }
        },
    });
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // click on 'Create' -> should open the quick create in the first column
    await createKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect(".o_field_widget[name=int_field] input").toHaveValue("4", {
        message: "default value should be set",
    });

    // fill the 'foo' field -> should trigger the onchange
    // await fieldInput("foo").edit("new partner");
    await editKanbanRecordQuickCreateInput("foo", "new partner");

    expect(".o_field_widget[name=int_field] input").toHaveValue("8", {
        message: "onchange should have been triggered",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "get_views", // form view in quick create
        "onchange", // quick create
        "onchange", // onchange due to 'foo' field change
    ]);
});

test("quick create record with quick_create_view: modifiers", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo" required="1"/>
            <field name="int_field" invisible="not foo"/>
        </form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // create a new record
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create .o_field_widget[name=foo]").toHaveClass("o_required_modifier");
    expect(".o_kanban_quick_create .o_field_widget[name=int_field]").toHaveCount(0);

    // fill 'foo' field
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await animationFrame();

    expect(".o_kanban_quick_create .o_field_widget[name=int_field]").toHaveCount(1);
});

test("quick create record with onchange of field marked readonly", async () => {
    Partner._fields.foo = fields.Char({
        onChange: (obj) => {
            obj.int_field = 8;
        },
    });
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field" readonly="true"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("web_save", ({ method, args }) => {
        expect(args[1].int_field).toBe(undefined, {
            message: "readonly field shouldn't be sent in create",
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
    ]);

    // click on 'Create' -> should open the quick create in the first column
    await quickCreateKanbanRecord();
    expect.verifySteps(["get_views", "onchange"]);

    // fill the 'foo' field -> should trigger the onchange
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    expect.verifySteps(["onchange"]);

    await validateKanbanRecord();
    expect.verifySteps(["web_save", "onchange", "web_read"]);
});

test("quick create record and change state in grouped mode", async () => {
    Partner._fields.kanban_state = fields.Selection({
        selection: [
            ["normal", "Grey"],
            ["done", "Green"],
            ["blocked", "Red"],
        ],
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <footer>
                            <field name="kanban_state" widget="state_selection"/>
                        </footer>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    // Quick create kanban record
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "Test");
    await validateKanbanRecord();

    // Select state in kanban
    await click(".o_status", { root: getKanbanRecord({ index: 0 }) });
    await animationFrame();
    await contains(".dropdown-item:nth-child(2)").click();

    expect(".o_status:first").toHaveClass("o_status_green");
});

test("window resize should not change quick create form size", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create .o_form_view").toHaveClass("o_xxs_form_view");

    await resize({ width: 800, height: 400 });

    expect(".o_kanban_quick_create .o_form_view").toHaveClass("o_xxs_form_view");
});

test("quick create record: cancel and validate without using the buttons", async () => {
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban quick_create_view="some_view_ref" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    // click to add an element and cancel the quick creation by pressing ESC
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);

    await press("Escape");
    await animationFrame();

    expect(".o_kanban_quick_create").toHaveCount(0);

    // click to add and element and click outside, should cancel the quick creation
    await quickCreateKanbanRecord();
    await contains(".o_control_panel").click();
    expect(".o_kanban_quick_create").toHaveCount(0);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    // click to input and drag the mouse outside, should not cancel the quick creation
    await quickCreateKanbanRecord();
    await (
        await drag(".o_kanban_quick_create input")
    ).drop(".o_kanban_group:first-child .o_kanban_record:last-of-type");
    await animationFrame();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been destroyed after clicking outside",
    });
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    // edit and confirm by pressing ENTER
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await press("Enter");
    await animationFrame();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);
    expect(getKanbanRecordTexts(0)).toEqual(["new partner", "blip"]);
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been reopened",
    });

    // clicking outside should no longer destroy the quick create as it is dirty, but save it
    await editKanbanRecordQuickCreateInput("foo", "new partner 2");
    await contains(".o_control_panel").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(6);
    expect(getKanbanRecordTexts(0)).toEqual(["new partner 2", "new partner", "blip"]);
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "the quick create should now be closed",
    });
});

test("quick create record: validate with ENTER", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4);

    // add an element and confirm by pressing ENTER
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("");
});

test("quick create record: prevent multiple adds with ENTER", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    const def = new Deferred();
    onRpc("web_save", () => {
        expect.step("web_save");
        return def;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4);

    // add an element and press ENTER twice
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await press("Enter");
    await animationFrame();

    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("new partner");
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    def.resolve();
    await animationFrame();

    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("");
    expect(".o_kanban_quick_create").not.toHaveClass("o_disabled");

    expect.verifySteps(["web_save"]);
});

test("quick create record: prevent multiple adds with Add clicked", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    const def = new Deferred();
    onRpc("web_save", () => {
        expect.step("web_save");
        return def;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4);

    // add an element and click 'Add' twice
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await validateKanbanRecord();
    await validateKanbanRecord();

    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("new partner");
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    def.resolve();
    await animationFrame();

    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("");
    expect(".o_kanban_quick_create").not.toHaveClass("o_disabled");

    expect.verifySteps(["web_save"]);
});

test.tags("desktop");
test("save a quick create record and create a new one simultaneously", async () => {
    const def = new Deferred();

    onRpc("name_create", () => {
        expect.step("name_create");
        return def;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4);

    // Create and save a record
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await validateKanbanRecord();
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("new partner");
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    // Create a new record during the save of the first one
    await createKanbanRecord();
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("new partner");
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    def.resolve();
    await animationFrame();
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("");
    expect(".o_kanban_quick_create").not.toHaveClass("o_disabled");
    expect.verifySteps(["name_create"]);
});

test("quick create record: prevent multiple adds with ENTER, with onchange", async () => {
    Partner._fields.foo = fields.Char({
        onChange: (obj) => {
            obj.int_field += obj.foo ? 3 : 0;
        },
    });
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    onRpc("onchange", () => {
        expect.step("onchange");
        if (shouldDelayOnchange) {
            return def;
        }
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const values = args[1];
        expect(values.foo).toBe("new partner");
        expect(values.int_field).toBe(3);
    });

    let shouldDelayOnchange = false;
    const def = new Deferred();
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4, {
        message: "should have 4 records at the beginning",
    });

    // add an element and press ENTER twice
    await quickCreateKanbanRecord();
    shouldDelayOnchange = true;
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await press("Enter");
    await animationFrame();
    await press("Enter");
    await animationFrame();

    expect(".o_kanban_record").toHaveCount(4, {
        message: "should not have created the record yet",
    });
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("new partner", {
        message: "quick create should not be empty yet",
    });
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    def.resolve();
    await animationFrame();

    expect(".o_kanban_record").toHaveCount(5, { message: "should have created a new record" });
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("", {
        message: "quick create should now be empty",
    });
    expect(".o_kanban_quick_create").not.toHaveClass("o_disabled");

    expect.verifySteps([
        "onchange", // default_get
        "onchange", // new partner
        "web_save",
        "onchange", // default_get
    ]);
});

test("quick create record: click Add to create, with delayed onchange", async () => {
    Partner._fields.foo = fields.Char({
        onChange: (obj) => {
            obj.int_field += obj.foo ? 3 : 0;
        },
    });
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="foo"/>
            <field name="int_field"/>
        </form>`;

    onRpc("onchange", () => {
        expect.step("onchange");
        if (shouldDelayOnchange) {
            return def;
        }
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            foo: "new partner",
            int_field: 3,
        });
    });

    let shouldDelayOnchange = false;
    const def = new Deferred();
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(4, {
        message: "should have 4 records at the beginning",
    });

    // add an element and click 'add'
    await quickCreateKanbanRecord();
    shouldDelayOnchange = true;
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_record").toHaveCount(4, {
        message: "should not have created the record yet",
    });
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("new partner", {
        message: "quick create should not be empty yet",
    });
    expect(".o_kanban_quick_create").toHaveClass("o_disabled");

    def.resolve(); // the onchange returns

    await animationFrame();
    expect(".o_kanban_record").toHaveCount(5, { message: "should have created a new record" });
    expect(".o_kanban_quick_create .o_field_widget[name=foo] input").toHaveValue("", {
        message: "quick create should now be empty",
    });
    expect(".o_kanban_quick_create").not.toHaveClass("o_disabled");

    expect.verifySteps([
        "onchange", // default_get
        "onchange", // new partner
        "web_save",
        "onchange", // default_get
    ]);
});

test.tags("desktop");
test("quick create when first column is folded", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child").not.toHaveClass("o_column_folded");
    expect(".o_kanban_group:nth-child(2)").not.toHaveClass("o_column_folded");

    // fold the first column
    let clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Fold");

    expect(".o_kanban_group:first-child").toHaveClass("o_column_folded");
    expect(".o_kanban_group:nth-child(2)").not.toHaveClass("o_column_folded");

    expect(".o_kanban_quick_create").toHaveCount(0);

    // click on 'Create' to open the quick create in the first non-folded column (second column)
    await createKanbanRecord();

    expect(".o_kanban_group:first-child").toHaveClass("o_column_folded");
    expect(".o_kanban_group:nth-child(2)").not.toHaveClass("o_column_folded");

    expect(".o_kanban_group:nth-child(2) .o_kanban_quick_create").toHaveCount(1);

    // fold again the second column
    clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Fold");

    expect(".o_kanban_group:first-child").toHaveClass("o_column_folded");
    expect(".o_kanban_group:nth-child(2)").toHaveClass("o_column_folded");

    expect(".o_kanban_quick_create").toHaveCount(0);

    // click on 'Create' to open the quick create in the first column since all columns are folded
    await createKanbanRecord();

    expect(".o_kanban_group:first-child").not.toHaveClass("o_column_folded");
    expect(".o_kanban_group:nth-child(2)").toHaveClass("o_column_folded");

    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
});

test("quick create record: cancel when not dirty", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should contain one record",
    });

    // click to add an element
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    // click again to add an element -> should have kept the quick create open
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have kept the quick create open",
    });

    // click outside: should remove the quick create
    await contains(".o_kanban_group:first-child .o_kanban_record:last-of-type").click();
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "the quick create should not have been destroyed",
    });

    // click to reopen the quick create
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    // press ESC: should remove the quick create
    await press("Escape");
    await animationFrame();

    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "quick create widget should have been removed",
    });

    // click to reopen the quick create
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    // click on 'Discard': should remove the quick create
    await quickCreateKanbanRecord();
    await discardKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "the quick create should be destroyed when the user clicks outside",
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should still contain one record",
    });

    // click to reopen the quick create
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    // clicking on the quick create itself should keep it open
    await contains(".o_kanban_quick_create").click();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been destroyed when clicked on itself",
    });
});

test.tags("desktop");
test("quick create record: cancel when modal is opened", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="product_id"/>
            <field name="foo"/>
        </form>
    `;
    Product._views.form = '<form><field name="name"/></form>';

    await mountView({
        type: "kanban",
        resModel: "partner",
        groupBy: ["bar"],
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    // click to add an element
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1);

    await press("t");
    await press("e");
    await press("s");
    await press("t");
    await runAllTimers();
    await click(".o_m2o_dropdown_option_create_edit"); // open create and edit dialog
    await animationFrame();

    // When focusing out of the many2one, a modal to add a 'product' will appear.
    // The following assertions ensures that a click on the body element that has 'modal-open'
    // will NOT close the quick create.
    // This can happen when the user clicks out of the input because of a race condition between
    // the focusout of the m2o and the global 'click' handler of the quick create.
    // Check odoo/odoo#61981 for more details.
    expect(".o_dialog").toHaveCount(1, { message: "modal should be opening after m2o focusout" });
    expect(document.body).toHaveClass("modal-open");
    await click(document.body);
    await animationFrame();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "quick create should stay open while modal is opening",
    });
});

test("quick create record: cancel when dirty", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should contain one record",
    });

    // click to add an element and edit it
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    await editKanbanRecordQuickCreateInput("display_name", "some value");

    // click outside: should create the record
    await contains(".o_kanban_group:first-child .o_kanban_record").click();
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "the quick create should not have been destroyed",
    });

    // click to reopen quick create and edit it
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "should have open the quick create widget",
    });

    await editKanbanRecordQuickCreateInput("display_name", "some value");

    // click on 'Discard': should remove the quick create
    await discardKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "the quick create should be destroyed when the user discard quick creation",
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
});

test("quick create record and edit in grouped mode", async () => {
    expect.assertions(4);

    onRpc("web_read", ({ args }) => {
        newRecordID = args[0][0];
    });

    let newRecordID;
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        selectRecord: (resId) => {
            expect(resId).toBe(newRecordID);
        },
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should contain one record",
    });

    // click to add and edit a record
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await editKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column should now contain two records",
    });
    expect(queryAllTexts(".o_kanban_group:first-child .o_kanban_record")).toEqual([
        "new partner",
        "blip",
    ]);
});

test.tags("desktop");
test("quick create several records in a row", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should contain one record",
    });

    // click to add an element, fill the input and press ENTER
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1, { message: "the quick create should be open" });

    await editKanbanRecordQuickCreateInput("display_name", "new partner 1");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column should now contain two records",
    });
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should still be open",
    });

    // create a second element in a row
    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new partner 2");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3, {
        message: "first column should now contain three records",
    });
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should still be open",
    });
});

test("quick create is re-enabled directly after the validation", async () => {
    let webSaveDef;
    let webReadDef;
    onRpc("web_save", () => webSaveDef);
    onRpc("web_read", () => webReadDef);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should contain one record",
    });

    // click to add a record, and add two in a row (first one will be delayed)
    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1, { message: "the quick create should be open" });

    await editKanbanRecordQuickCreateInput("display_name", "new partner 1");
    webSaveDef = new Deferred();
    webReadDef = new Deferred();
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should still contain one record",
    });
    expect(".o_kanban_quick_create.o_disabled").toHaveCount(0, {
        message: "quick create should be enabled",
    });

    webSaveDef.resolve();
    await animationFrame();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should still contain one record",
    });
    expect(".o_kanban_quick_create.o_disabled").toHaveCount(0, {
        message: "quick create should be enabled",
    });

    webReadDef.resolve();
    await animationFrame();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column should now contain two records",
    });
    expect(".o_kanban_quick_create.o_disabled").toHaveCount(0, {
        message: "quick create should be enabled",
    });
});

test.tags("desktop");
test("quick create record fail in grouped by many2one", async () => {
    Partner._views["form"] = `
        <form>
            <field name="product_id"/>
            <field name="foo"/>
        </form>`;

    onRpc("name_create", () => {
        throw makeServerError({ message: "This is a user error" });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);

    await createKanbanRecord();
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await validateKanbanRecord();
    expect(".modal .o_form_view .o_form_editable").toHaveCount(1);
    expect(".modal .o_field_many2one input:first").toHaveValue("hello");

    // specify a name and save
    await contains(".modal .o_field_widget[name=foo] input").edit("test");
    await contains(".modal .o_form_button_save").click();
    expect(".modal").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group .o_kanban_record:first").toHaveText("test");
    expect(".o_kanban_quick_create:not(.o_disabled)").toHaveCount(1);
});

test("quick create record and click Edit, name_create fails", async () => {
    Partner._views["kanban"] = `
        <kanban sample="1">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;
    Partner._views["list"] = '<list><field name="foo"/></list>';
    Partner._views["form"] = `
        <form>
            <field name="product_id"/>
            <field name="foo"/>
        </form>`;

    onRpc("name_create", () => {
        throw makeServerError({ message: "This is a user error" });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
        context: {
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);

    await quickCreateKanbanRecord(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await editKanbanRecord();
    expect(".modal .o_form_view .o_form_editable").toHaveCount(1);
    expect(".modal .o_field_many2one input:first").toHaveValue("hello");

    // specify a name and save
    await contains(".modal .o_field_widget[name=foo] input").edit("test");
    await contains(".modal .o_form_button_save").click();
    expect(".modal").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group .o_kanban_record:first").toHaveText("test");
    expect(".o_kanban_quick_create:not(.o_disabled)").toHaveCount(1);
});

test.tags("desktop");
test("quick create record is re-enabled after discard on failure", async () => {
    Partner._views["form"] = `
        <form>
            <field name="product_id"/>
            <field name="foo"/>
        </form>`;

    onRpc("name_create", () => {
        throw makeServerError({ message: "This is a user error" });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);

    await createKanbanRecord();
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await validateKanbanRecord();
    expect(".modal .o_form_view .o_form_editable").toHaveCount(1);

    await contains(".modal .o_form_button_cancel").click();
    expect(".modal .o_form_view .o_form_editable").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);
});

test("quick create record fails in grouped by char", async () => {
    expect.assertions(7);

    Partner._views["form"] = '<form><field name="foo"/></form>';

    onRpc("name_create", () => {
        throw makeServerError({ message: "This is a user error" });
    });
    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ foo: "blip" });
        expect(kwargs.context).toEqual({
            allowed_company_ids: [1],
            default_foo: "blip",
            default_name: "test",
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        groupBy: ["foo"],
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "test");
    await validateKanbanRecord();

    expect(".modal .o_form_view .o_form_editable").toHaveCount(1);
    expect(".modal .o_field_widget[name=foo] input").toHaveValue("blip");
    await contains(".modal .o_form_button_save").click();

    expect(".modal .o_form_view .o_form_editable").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(3);
});

test("quick create record fails in grouped by selection", async () => {
    expect.assertions(7);

    Partner._views["form"] = '<form><field name="state"/></form>';

    onRpc("name_create", () => {
        throw makeServerError({ message: "This is a user error" });
    });
    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ state: "abc" });
        expect(kwargs.context).toEqual({
            allowed_company_ids: [1],
            default_state: "abc",
            default_name: "test",
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        groupBy: ["state"],
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="state"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(1);

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "test");
    await validateKanbanRecord();

    expect(".modal .o_form_view .o_form_editable").toHaveCount(1);
    expect(".modal .o_field_widget[name=state] input").toHaveValue("ABC");

    await contains(".modal .o_form_button_save").click();

    expect(".modal .o_form_view .o_form_editable").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);
});

test.tags("desktop");
test("quick create record in empty grouped kanban", async () => {
    onRpc("web_read_group", () =>
        // override web_read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        ({
            groups: [
                {
                    __extra_domain: [["product_id", "=", 3]],
                    __count: 0,
                    product_id: [3, "xplone"],
                },
                {
                    __extra_domain: [["product_id", "=", 5]],
                    __count: 0,
                    product_id: [5, "xplan"],
                },
            ],
            length: 2,
        })
    );

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be 2 columns" });
    expect(".o_kanban_record").toHaveCount(0, { message: "both columns should be empty" });

    await createKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1, {
        message: "should have opened the quick create in the first column",
    });
});

test.tags("desktop");
test("quick create record in grouped on date(time) field", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_datetime" domain="[]" string="GroupBy Datetime" context="{ 'group_by': 'datetime' }"/>
            </search>`,
        groupBy: ["date"],
        createRecord: () => {
            expect.step("createKanbanRecord");
        },
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(0, {
        message: "quick create should be disabled when grouped on a date field",
    });

    // clicking on CREATE in control panel should not open a quick create
    await createKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "should not have opened the quick create widget",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Datetime");

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(0, {
        message: "quick create should be disabled when grouped on a datetime field",
    });

    // clicking on CREATE in control panel should not open a quick create
    await createKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "should not have opened the quick create widget",
    });

    expect.verifySteps(["createKanbanRecord", "createKanbanRecord"]);
});

test("quick create record feature is properly enabled/disabled at reload", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_date" domain="[]" string="GroupBy Date" context="{ 'group_by': 'date' }"/>
                <filter name="group_by_bar" domain="[]" string="GroupBy Bar" context="{ 'group_by': 'bar' }"/>
            </search>`,
        groupBy: ["foo"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(3, {
        message: "quick create should be enabled when grouped on a char field",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Date");
    await toggleMenuItemOption("GroupBy Date", "Month");

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(0, {
        message: "quick create should now be disabled (grouped on date field)",
    });

    await toggleMenuItemOption("GroupBy Date", "Month");
    await toggleMenuItem("GroupBy Bar");

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(2, {
        message: "quick create should be enabled again (grouped on boolean field)",
    });
});

test("quick create record in grouped by char field", async () => {
    expect.assertions(4);

    onRpc("name_create", ({ kwargs }) => {
        expect(kwargs.context.default_foo).toBe("blip");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(3);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new record");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);
});

test("quick create record in grouped by boolean field", async () => {
    expect.assertions(4);

    onRpc("name_create", ({ kwargs }) => {
        expect(kwargs.context.default_bar).toBe(true);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(2);
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3);

    await quickCreateKanbanRecord(1);
    await editKanbanRecordQuickCreateInput("display_name", "new record");
    await validateKanbanRecord();

    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(4);
});

test("quick create record in grouped on selection field", async () => {
    expect.assertions(4);

    onRpc("name_create", ({ kwargs }) => {
        expect(kwargs.context.default_state).toBe("abc");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["state"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(3, {
        message: "quick create should be enabled when grouped on a selection field",
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column (abc) should contain 1 record",
    });

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new record");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column (abc) should contain 2 records",
    });
});

test("quick create record in grouped by char field (within quick_create_view)", async () => {
    expect.assertions(6);

    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ foo: "blip" });
        expect(kwargs.context.default_foo).toBe("blip");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(3);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create input:first").toHaveValue("blip", {
        message: "should have set the correct foo value by default",
    });
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);
});

test("quick create record in grouped by boolean field (within quick_create_view)", async () => {
    expect.assertions(6);

    Partner._views["form,some_view_ref"] = `<form><field name="bar"/></form>`;

    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ bar: true });
        expect(kwargs.context.default_bar).toBe(true);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="bar"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(2, {
        message: "quick create should be enabled when grouped on a boolean field",
    });
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_quick_create .o_field_boolean input").toBeChecked();

    await contains(".o_kanban_quick_create .o_kanban_add").click();
    await animationFrame();
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(4);
});

test("quick create record in grouped by selection field (within quick_create_view)", async () => {
    expect.assertions(6);

    Partner._views["form,some_view_ref"] = `<form><field name="state"/></form>`;

    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1]).toEqual({ state: "abc" });
        expect(kwargs.context.default_state).toBe("abc");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="state"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["state"],
    });

    expect(".o_kanban_header .o_kanban_quick_add i").toHaveCount(3, {
        message: "quick create should be enabled when grouped on a selection field",
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column (abc) should contain 1 record",
    });

    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create input").toHaveValue("ABC", {
        message: "should have set the correct state value by default",
    });

    await contains(".o_kanban_quick_create .o_kanban_add").click();
    await animationFrame();
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column (abc) should now contain 2 records",
    });
});

test.tags("desktop");
test("quick create record while adding a new column", async () => {
    const def = new Deferred();
    onRpc("product", "name_create", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    // add a new column
    expect(".o_column_quick_create.o_quick_create_folded").toHaveCount(1);

    await quickCreateKanbanColumn();

    expect(".o_column_quick_create.o_quick_create_unfolded").toHaveCount(1);

    await editKanbanColumnName("new column");
    await validateKanbanColumn();

    await animationFrame();

    expect(".o_column_quick_create input:first").toHaveValue("");
    expect(".o_kanban_group").toHaveCount(2);

    // click to add a new record
    await createKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);

    // unlock column creation
    def.resolve();
    await animationFrame();

    expect(".o_kanban_group").toHaveCount(3);
    expect(".o_kanban_quick_create").toHaveCount(1);

    // quick create record in first column
    await editKanbanRecordQuickCreateInput("display_name", "new record");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);
});

test.tags("desktop");
test("close a column while quick creating a record", async () => {
    Partner._views["form,some_view_ref"] = '<form><field name="int_field"/></form>';

    let def;
    onRpc("get_views", () => {
        if (def) {
            expect.step("get_views");
            return def;
        }
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    def = new Deferred();

    expect.verifySteps([]);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_column_folded").toHaveCount(0);

    // click to quick create a new record in the first column (this operation is delayed)
    await quickCreateKanbanRecord();

    expect.verifySteps(["get_views"]);
    expect(".o_form_view").toHaveCount(0);

    // click to fold the first column
    const clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Fold");

    expect(".o_column_folded").toHaveCount(1);

    def.resolve();
    await animationFrame();

    expect.verifySteps([]);
    expect(".o_form_view").toHaveCount(0);
    expect(".o_column_folded").toHaveCount(1);

    await createKanbanRecord();

    expect.verifySteps([]); // "get_views" should have already be done
    expect(".o_form_view").toHaveCount(1);
    expect(".o_column_folded").toHaveCount(1);
});

test("quick create record: open on a column while another column has already one", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // Click on quick create in first column
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);

    // Click on quick create in second column
    await quickCreateKanbanRecord(1);
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(2) })).toHaveCount(1);

    // Click on quick create in first column once again
    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);
});

test("remove nocontent helper after adding a record", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => ({
        groups: [
            {
                __extra_domain: [["product_id", "=", 3]],
                __count: 0,
                product_id: [3, "hello"],
                __records: [],
            },
        ],
        length: 1,
    }));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    expect(".o_view_nocontent").toHaveCount(1, { message: "there should be a nocontent helper" });

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "twilight sparkle");
    await validateKanbanRecord();

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (there is now one record)",
    });
});

test("remove nocontent helper when adding a record", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => ({
        groups: [
            {
                __extra_domain: [["product_id", "=", 3]],
                __count: 0,
                product_id: [3, "hello"],
                __records: [],
            },
        ],
        length: 1,
    }));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    expect(".o_view_nocontent").toHaveCount(1, { message: "there should be a nocontent helper" });

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "twilight sparkle");

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (there is now one record)",
    });
});

test("nocontent helper is displayed again after canceling quick create", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => ({
        groups: [
            {
                __extra_domain: [["product_id", "=", 3]],
                __count: 0,
                product_id: [3, "hello"],
                __records: [],
            },
        ],
        length: 1,
    }));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    await quickCreateKanbanRecord();
    await press("Escape");
    await animationFrame();

    expect(".o_view_nocontent").toHaveCount(1, {
        message: "there should be again a nocontent helper",
    });
});

test("empty grouped kanban with sample data and click quick create", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override web_read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group.__count = 0;
        });
        return result;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban sample="1">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be two columns" });
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(16, {
        message: "there should be 8 sample records by column",
    });
    expect(queryAllTexts(".o_column_title")).toEqual(["hello", "xmo"]);

    await quickCreateKanbanRecord();
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(0)", "xmo\n(0)"]);

    await editKanbanRecordQuickCreateInput("display_name", "twilight sparkle");
    await validateKanbanRecord();

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(1)", "xmo\n(0)"]);
});

test("empty grouped kanban with sample data and cancel quick create", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override web_read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group.__count = 0;
        });
        return result;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban sample="1">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });
    expect(".o_kanban_group").toHaveCount(2, { message: "there should be two columns" });
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(16, {
        message: "there should be 8 sample records by column",
    });

    await quickCreateKanbanRecord();
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);

    await contains(".o_kanban_view").click();
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_quick_create").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(1);
});

test.tags("desktop");
test("quick create record in grouped kanban with sample data", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override web_read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group.__count = 0;
        });
        return result;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban sample="1" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be two columns" });
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(16, {
        message: "there should be 8 sample records by column",
    });

    await createKanbanRecord();
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record").toHaveCount(0);
    expect(".o_kanban_load_more").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(queryAll(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);
});

test.tags("desktop");
test("quickcreate in first column after moving a record from it", async () => {
    onRpc("web_resequence", () => []);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    await createKanbanRecord();

    expect(queryFirst(".o_kanban_group:has(.o_kanban_quick_create)")).toBe(
        queryFirst(".o_kanban_group")
    );

    await contains(".o_kanban_record").dragAndDrop(".o_kanban_group:nth-child(2)");
    await createKanbanRecord();

    expect(queryFirst(".o_kanban_group:has(.o_kanban_quick_create)")).toBe(
        queryFirst(".o_kanban_group")
    );
});

test.tags("desktop");
test("quick_create on grouped kanban without column", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        // force group_create to false, otherwise the CREATE button in control panel is hidden
        arch: `
            <kanban group_create="0" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        createRecord: () => {
            expect.step("createKanbanRecord");
        },
    });

    await createKanbanRecord();
    expect.verifySteps(["createKanbanRecord"]);
});

test.tags("desktop");
test("quick create: keyboard navigation to buttons", async () => {
    await mountView({
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="display_name"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        resModel: "partner",
        type: "kanban",
    });

    // Open quick create
    await createKanbanRecord();
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);

    // Fill in mandatory field
    await editKanbanRecordQuickCreateInput("display_name", "aaa"); // pressed Tab to trigger "change"
    expect(".o_kanban_add").toBeFocused();

    await press("Tab");
    expect(".o_kanban_edit").toBeFocused();
});

test.tags("desktop");
test("quick create: press 'Enter' on trash icon", async () => {
    await mountView({
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="display_name"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        resModel: "partner",
        type: "kanban",
    });

    await createKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1);
    await press("Tab");
    await press("Tab");
    await press("Tab");
    expect(".o_kanban_cancel").toBeFocused();
    await press("Enter");
    await animationFrame();
    expect(".o_kanban_quick_create").toHaveCount(0);
});

test("Quick created record is rendered after load", async () => {
    let def;
    onRpc("web_read", () => {
        expect.step("web_read");
        return def;
    });
    onRpc("name_create", () => {
        expect.step("name_create");
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <field name="category_ids" />
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <span t-esc="record.category_ids.raw_value.length" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(getKanbanRecordTexts(0)).toEqual(["0", "1"]);
    expect.verifySteps([]);

    def = new Deferred();

    await quickCreateKanbanRecord(0);
    await editKanbanRecordQuickCreateInput("display_name", "Test");
    await validateKanbanRecord();
    expect(getKanbanRecordTexts(0)).toEqual(["0", "1"]);

    def.resolve();
    await animationFrame();

    expect(getKanbanRecordTexts(0)).toEqual(["0", "0", "1"]);
    expect.verifySteps(["name_create", "web_read"]);
});

test.tags("desktop");
test("quick create record and click outside (no dirty input)", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="2">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await contains(".o_control_panel").click();

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await quickCreateKanbanRecord(1);

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_quick_create").toHaveCount(1);

    await contains(".o_kanban_load_more button").click();

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);
});

test.tags("desktop");
test("quick create record and click outside (with dirty input)", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="2">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_record").toHaveCount(3);
    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "ABC");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("ABC");

    await contains(".o_control_panel").click();

    expect(".o_kanban_quick_create").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("");

    await editKanbanRecordQuickCreateInput("display_name", "DEF");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("DEF");

    await contains(".o_kanban_load_more button").click();

    expect(".o_kanban_quick_create").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(6); // 4 + 1 created record + 1 "load more" record

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "GHI");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("GHI");
});

test("quick create record and click on 'Load more'", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="2">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord(1);

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    await contains(".o_kanban_load_more button").click();

    expect(".o_kanban_quick_create").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
});

test.tags("desktop");
test("quick create record in grouped kanban in a form view dialog", async () => {
    Partner._fields.foo = fields.Char({ default: "ABC" });
    Partner._views["form"] = `<form><field name="bar"/></form>`;

    onRpc("name_create", ({ method }) => {
        throw makeServerError();
    });
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <t t-if="record.foo.raw_value" t-set="foo"/>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "first column should contain two records",
    });
    expect(queryAllTexts(".o_kanban_group:first-child .o_kanban_record")).toEqual(["yop", "gnap"]);
    expect(".modal").toHaveCount(0);

    // click on 'Create', fill the quick create and validate
    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await validateKanbanRecord();

    expect(".modal").toHaveCount(1);

    await clickModalButton({ text: "Save" });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3, {
        message: "first column should contain three records",
    });
    expect(queryAllTexts(".o_kanban_group:first-child .o_kanban_record")).toEqual([
        "ABC",
        "yop",
        "gnap",
    ]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // initial web_read_group
        "has_group",
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "get_views", // load views for form view dialog
        "onchange", // load of a virtual record in form view dialog
        "web_save", // save virtual record
        "web_read", // read the created record to get foo value
        "onchange", // reopen the quick create automatically
    ]);
});

test("click on New while kanban is loading (with quick create)", async () => {
    onRpc("web_read_group", () => new Deferred());
    await mountView({
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
        createRecord: () => expect.step("create record"),
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_view .o_control_panel").toHaveCount(1);
    expect(".o_kanban_view .o_kanban_renderer").toHaveCount(0);

    await createKanbanRecord();
    expect.verifySteps(["create record"]);
});

test.tags("desktop");
test("grouped kanban with quick_create attrs set to false", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban quick_create="false" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        createRecord: () => expect.step("create record"),
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_quick_add").toHaveCount(0);

    await createKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(0);
    expect.verifySteps(["create record"]);
});

test("quick create record and leave before validating (no quick create view)", async () => {
    Partner._views.list = `<list><field name="foo"/></list>`;
    Partner._views.kanban = `
        <kanban>
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;

    onRpc("name_create", ({ args }) => {
        expect.step("name_create");
        expect(args[0]).toBe("test");
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: {
            group_by: ["product_id"],
        },
    });

    await quickCreateKanbanRecord(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    expect.verifySteps([]);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    expect(".o_list_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(5);
    expect.verifySteps(["name_create"]);
});

test("quick create record and leave before validating (with quick create view)", async () => {
    Partner._views["form,quick_create_ref"] = `<form><field name="foo"/></form>`;
    Partner._views.list = `<list><field name="foo"/></list>`;
    Partner._views.kanban = `
        <kanban quick_create_view="quick_create_ref">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ foo: "test" });
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: {
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    expect.verifySteps([]);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    expect(".o_list_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(5);
    expect.verifySteps(["web_save"]);
});

test("quick create record and leave before validating (not dirty)", async () => {
    Partner._views["form,quick_create_ref"] = `<form><field name="foo"/></form>`;
    Partner._views.list = `<list><field name="foo"/></list>`;
    Partner._views.kanban = `
        <kanban quick_create_view="quick_create_ref">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: {
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    expect(".o_list_view").toHaveCount(1); // kanban has been left
    expect(".o_data_row").toHaveCount(4); // no record created
});

test("quick create record and leave before validating (dirty and invalid)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;
    Partner._views.list = `<list><field name="foo"/></list>`;
    Partner._views.kanban = `
        <kanban quick_create_view="quick_create_ref">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: {
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(0);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    expect.verifySteps([]);

    getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    await animationFrame();
    expect(".o_list_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=date]").toHaveClass("o_field_invalid");
});

test("click on New while quick create is open (in first column)", async () => {
    await mountView({
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await createKanbanRecord();
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await createKanbanRecord();
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveValue("");
});

test("click on New while quick create is open (first column, quick create view)", async () => {
    Partner._views["form,form_view_ref"] = `<form><field name="foo"/></form>`;
    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="form_view_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["product_id"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await createKanbanRecord();
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    await createKanbanRecord();
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveValue("");
});

test("click on New while quick create is open (not in first column)", async () => {
    await mountView({
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await createKanbanRecord();
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_group:first .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveValue("");
});

test("click on New while quick create is open (invalid)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;
    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    await createKanbanRecord();
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=foo] input").toHaveValue("test");
    expect(".o_kanban_quick_create [name=date]").toHaveClass("o_field_invalid");
});

test("click on '+' while quick create is open (in same column)", async () => {
    await mountView({
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await quickCreateKanbanRecord(1);
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveValue("");
});

test("click on '+' while quick create is open (in another column)", async () => {
    await mountView({
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await quickCreateKanbanRecord(2);
    expect(".o_kanban_record").toHaveCount(5);
    expect(".o_kanban_group:eq(2) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create input").toHaveValue("");
});

test("click on '+' while quick create is open (invalid)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;
    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    await quickCreateKanbanRecord(2);
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=foo] input").toHaveValue("test");
    expect(".o_kanban_quick_create [name=date]").toHaveClass("o_field_invalid");
});

test("click on '+' while quick create is open (not dirty)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;
    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(4);

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await quickCreateKanbanRecord(2);
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:eq(2) .o_kanban_quick_create").toHaveCount(1);
});

test("Auto save on closing tab/browser (no quick create view)", async () => {
    onRpc("partner", "name_create", ({ args }) => {
        expect.step("name_create"); // should be called
        expect(args[0]).toEqual("test");
    });

    await mountView({
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");

    const [event] = await unload();
    expect(event.defaultPrevented).toBe(false);
    expect.verifySteps(["name_create"]);
});

test("Auto save on closing tab/browser (quick create view)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
        </form>`;

    const sendBeaconDeferred = new Deferred();
    mockSendBeacon((_, blob) => {
        expect.step("sendBeacon");
        blob.text().then((r) => {
            const { params } = JSON.parse(r);
            if (params.method === "web_save" && params.model === "partner") {
                expect(params.args[1]).toEqual({ foo: "test" });
            }
            sendBeaconDeferred.resolve();
        });
        return true;
    });
    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");

    const [event] = await unload();
    await animationFrame();
    expect(event.defaultPrevented).toBe(false);
    expect.verifySteps(["sendBeacon"]);
});

test("Auto save on closing tab/browser (invalid)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;

    mockSendBeacon(() => expect.step("sendBeacon"));

    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");

    const [event] = await unload();
    await animationFrame();
    expect(event.defaultPrevented).toBe(true);
    expect(".o_kanban_quick_create [name=date]").toHaveClass("o_field_invalid");
    expect.verifySteps([]);
});

test("Auto save on hiding tab (no quick create view)", async () => {
    onRpc("partner", "name_create", ({ args }) => {
        expect.step("name_create"); // should be called
        expect(args[0]).toEqual("test");
    });

    await mountView({
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "test");
    await hideTab();
    await animationFrame();
    expect.verifySteps(["name_create"]);
    expect(".o_kanban_quick_create").toHaveCount(0);
});

test("Auto save on hiding tab (quick create view)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
        </form>`;

    onRpc("partner", "web_save", ({ args }) => {
        expect.step("web_save"); // should be called
        expect(args[1]).toEqual({ foo: "test" });
    });

    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    await hideTab();
    await animationFrame();
    expect.verifySteps(["web_save"]);
    expect(".o_kanban_quick_create").toHaveCount(0);
});

test("Auto save on hiding tab (invalid)", async () => {
    Partner._views["form,quick_create_ref"] = `
        <form>
            <field name="foo"/>
            <field name="date" required="1"/>
        </form>`;

    onRpc("partner", "web_save", ({ args }) => {
        throw new Error("should not save");
    });

    await mountView({
        arch: `
            <kanban on_create="quick_create" quick_create_view="quick_create_ref">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
        groupBy: ["foo"],
    });

    await quickCreateKanbanRecord(1);
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("foo", "test");
    await hideTab();
    await animationFrame();
    expect(".o_kanban_group:eq(1) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create .o_field_widget[name=date]").toHaveClass("o_field_invalid");
});
