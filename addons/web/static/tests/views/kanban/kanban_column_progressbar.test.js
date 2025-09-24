import { beforeEach, expect, test } from "@odoo/hoot";
import {
    keyDown,
    keyUp,
    on,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryText,
    scroll,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import {
    clickKanbanLoadMore,
    contains,
    createKanbanRecord,
    defineModels,
    editKanbanColumnName,
    editKanbanRecordQuickCreateInput,
    fields,
    getDropdownMenu,
    getFacetTexts,
    getKanbanColumn,
    getKanbanColumnTooltips,
    getKanbanCounters,
    getKanbanProgressBars,
    getKanbanRecord,
    getKanbanRecordTexts,
    getMockEnv,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    quickCreateKanbanColumn,
    quickCreateKanbanRecord,
    serverState,
    stepAllNetworkCalls,
    toggleKanbanColumnActions,
    toggleMenuItem,
    toggleSearchBarMenu,
    validateKanbanColumn,
    validateKanbanRecord,
    validateSearch,
    webModels,
} from "@web/../tests/web_test_helpers";

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AnimatedNumber } from "@web/views/view_components/animated_number";
import { WebClient } from "@web/webclient/webclient";

const { IrAttachment } = webModels;

async function toggleMultiCurrencyPopover(el) {
    if (getMockEnv().isSmall) {
        await contains(el).click();
    } else {
        await contains(el).hover();
    }
}

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
    rate_date = fields.Date();

    _records = [
        {
            id: 1,
            name: "USD",
            symbol: "$",
            position: "before",
            inverse_rate: 1,
            rate_date: "2017-01-08",
        },
        {
            id: 2,
            name: "EUR",
            symbol: "€",
            position: "after",
            inverse_rate: 0.5,
            rate_date: "2019-06-13",
        },
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

test("Ensuring each progress bar has some space", async () => {
    Partner._records = [
        {
            id: 1,
            foo: "blip",
            state: "def",
        },
        {
            id: 2,
            foo: "blip",
            state: "abc",
        },
    ];

    for (let i = 0; i < 20; i++) {
        Partner._records.push({
            id: 3 + i,
            foo: "blip",
            state: "ghi",
        });
    }

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <div t-name="card">
                        <field name="state" widget="state_selection" />
                        <field name="foo" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["foo"],
    });

    expect(getKanbanProgressBars(0).map((pb) => pb.style.width)).toEqual(["5%", "5%", "90%"]);
});

test("column progressbars properly work", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_counter").toHaveCount(2, {
        message: "kanban counters should have been created",
    });

    expect(getKanbanCounters()).toEqual(["-4", "36"], {
        message: "counter should display the sum of int_field values",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
    ]);
});

test("filter on progressbar in new groups", async () => {
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id" on_create="quick_create" quick_create_view="some_view_ref">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_group").toHaveCount(2);

    await quickCreateKanbanColumn();
    await editKanbanColumnName("new column 1");
    await validateKanbanColumn();
    await editKanbanColumnName("new column 2");
    await validateKanbanColumn();
    expect(".o_kanban_group").toHaveCount(4);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(2) })).toHaveCount(0);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(3) })).toHaveCount(0);

    await quickCreateKanbanRecord(2);
    await contains(".o_field_widget[name=foo] input").edit("new record 1");
    await quickCreateKanbanRecord(3);
    await contains(".o_field_widget[name=foo] input").edit("new record 2");
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(2) })).toHaveCount(1);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(3) })).toHaveCount(1);

    expect(".o_kanban_group_show_200").toHaveCount(0);

    await contains(".o_column_progress .progress-bar", { root: getKanbanColumn(2) }).click();
    expect(".o_kanban_group_show_200").toHaveCount(1);
    expect(getKanbanColumn(2)).toHaveClass("o_kanban_group_show_200");
});

test('column progressbars: "false" bar is clickable', async () => {
    Partner._records.push({
        id: 5,
        bar: true,
        foo: false,
        product_id: 5,
        state: "ghi",
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(getKanbanCounters()).toEqual(["1", "4"]);
    expect(".o_kanban_group:last-child .o_column_progress .progress-bar").toHaveCount(4);
    expect(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200").toHaveCount(1, {
        message: "should have false kanban color",
    });
    expect(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200:first").toHaveClass(
        "bg-200"
    );

    await contains(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200").click();

    expect(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200:first").toHaveClass(
        "progress-bar-animated"
    );
    expect(".o_kanban_group:last-child").toHaveClass("o_kanban_group_show_200");
    expect(getKanbanCounters()).toEqual(["1", "1"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
    ]);
});

test('column progressbars: "false" bar with sum_field', async () => {
    Partner._records.push({
        id: 5,
        bar: true,
        foo: false,
        int_field: 15,
        product_id: 5,
        state: "ghi",
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(getKanbanCounters()).toEqual(["-4", "51"]);

    await contains(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200").click();

    expect(".o_kanban_group:last-child .o_column_progress .progress-bar.bg-200:first").toHaveClass(
        "progress-bar-animated"
    );
    expect(getKanbanCounters()).toEqual(["-4", "15"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "formatted_read_group",
        "web_search_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
    ]);
});

test("column progressbars should not crash in non grouped views", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual(["yop", "blip", "gnap", "blip"]);
    // no read on progress bar data is done
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test("column progressbars: creating a new column should create a new progressbar", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_counter").toHaveCount(2);

    // Create a new column: this should create an empty progressbar
    await quickCreateKanbanColumn();
    await editKanbanColumnName("test");
    await validateKanbanColumn();

    expect(".o_kanban_counter").toHaveCount(3, {
        message: "a new column with a new column progressbar should have been created",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "name_create",
        "web_resequence",
    ]);
});

test("column progressbars on quick create properly update counter", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanCounters()).toEqual(["1", "3"]);

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "Test");

    expect(getKanbanCounters()).toEqual(["1", "3"]);

    await validateKanbanRecord();

    expect(getKanbanCounters()).toEqual(["2", "3"], {
        message: "kanban counters should have updated on quick create",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "onchange",
        "name_create",
        "onchange",
        "web_read",
        "read_progress_bar",
    ]);
});

test("column progressbars are working with load more", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        domain: [["bar", "=", true]],
        arch: `
            <kanban limit="1">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanRecordTexts(0)).toEqual(["1"]);

    await clickKanbanLoadMore(0);
    await clickKanbanLoadMore(0);

    expect(getKanbanRecordTexts(0)).toEqual(["1", "2", "3"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test("column progressbars with an active filter are working with load more", async () => {
    Partner._records.push(
        { id: 5, bar: true, foo: "blork" },
        { id: 6, bar: true, foo: "blork" },
        { id: 7, bar: true, foo: "blork" }
    );

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        domain: [["bar", "=", true]],
        arch: `
            <kanban limit="1">
                <progressbar field="foo" colors='{"blork": "success"}'/>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await contains(".o_column_progress .progress-bar.bg-success").click();

    expect(getKanbanRecordTexts()).toEqual(["5"]);

    await clickKanbanLoadMore(0);
    await clickKanbanLoadMore(0);

    expect(getKanbanRecordTexts()).toEqual(["5", "6", "7"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "web_search_read",
        "web_search_read",
    ]);
});

test("column progressbars on archiving records update counter", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        loadActionMenus: true,
    });

    expect(getKanbanCounters()).toEqual(["-4", "36"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 gnap", "1 blip"], {
        message: "the counter progressbars should be correctly displayed",
    });

    // archive all records of the second columns
    await keyDown("alt");
    await animationFrame();
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(1)").click();
    await keyUp("alt");
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(2)").click();
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(3)").click();
    await contains(".o_cp_action_menus button").click();
    await contains(".o_menu_item:contains(Archive)").click();
    await contains(".modal-footer .btn-primary").click();

    expect(getKanbanCounters()).toEqual(["-4", "0"]);
    expect(queryAll(".progress-bar", { root: getKanbanColumn(1) })).toHaveCount(0, {
        message: "the counter progressbars should have been correctly updated",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "action_archive",
        "read_progress_bar",
        "web_read_group",
    ]);
});

test("kanban with progressbars: correctly update env when archiving records", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        loadActionMenus: true,
    });

    expect(getKanbanRecordTexts()).toEqual(["4", "1", "2", "3"]);

    // archive all records of the first column
    await keyDown("alt");
    await animationFrame();
    await contains(".o_kanban_group:nth-of-type(1) .o_kanban_record:nth-of-type(1)").click();
    await keyUp("alt");
    await contains(".o_cp_action_menus button").click();
    await contains(".o_menu_item:contains(Archive)").click();
    await contains(".modal-footer .btn-primary").click();

    expect(getKanbanRecordTexts()).toEqual(["1", "2", "3"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "action_archive",
        "read_progress_bar",
        "web_read_group",
    ]);
});

test("kanban with progressbars: slow read_progress_bar", async () => {
    const def = new Deferred();
    onRpc("read_progress_bar", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
            <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_column_progress").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_column_progress .progress-bar").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_header").toHaveText("Yes");

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_column_progress").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_column_progress .progress-bar").toHaveCount(3);
    expect(".o_kanban_group:nth-child(2) .o_kanban_header").toHaveText("Yes\n36");
});

test("RPCs when (re)loading kanban view progressbars", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
            <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`,
        groupBy: ["bar"],
    });

    await validateSearch();

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        // initial load
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        // reload
        "read_progress_bar",
        "web_read_group",
    ]);
});

test("RPCs when (de)activating kanban view progressbar filters", async () => {
    stepAllNetworkCalls();
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(`web_read_group domain ${JSON.stringify(kwargs.domain)}`);
    });
    onRpc("formatted_read_group", ({ kwargs }) => {
        expect.step(`formatted_read_group domain ${JSON.stringify(kwargs.domain)}`);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // Activate "yop" on second column
    await contains(".progress-bar.bg-success", { root: getKanbanColumn(1) }).click();
    // Activate "gnap" on second column
    await contains(".progress-bar.bg-warning", { root: getKanbanColumn(1) }).click();
    // Deactivate "gnap" on second column
    await contains(".progress-bar.bg-warning", { root: getKanbanColumn(1) }).click();

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        // initial load
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_read_group domain []",
        "formatted_read_group", // recomputes aggregates
        "web_search_read",
        'formatted_read_group domain ["&",["bar","=",true],["foo","=","yop"]]', // perform formatted_read_group only on second column (bar=true)
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
        "formatted_read_group domain []",
        'formatted_read_group domain ["&",["bar","=",true],["foo","=","yop"]]',
        // activate filter
        "formatted_read_group", // recomputes aggregates
        "web_search_read",
        'formatted_read_group domain ["&",["bar","=",true],["foo","=","gnap"]]', // perform formatted_read_group only on second column (bar=true)
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
        "formatted_read_group domain []",
        'formatted_read_group domain ["&",["bar","=",true],["foo","=","gnap"]]',
        // activate another filter (switching)
        "web_search_read",
    ]);
});

test.tags("desktop");
test("drag & drop records grouped by m2o with progressbar", async () => {
    Partner._records[0].product_id = false;

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // Unfold first column
    await contains(getKanbanColumn(0)).click();

    expect(getKanbanCounters()).toEqual(["1", "1", "2"]);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(getKanbanCounters()).toEqual(["0", "2", "2"]);

    await contains(".o_kanban_group:nth-child(2) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first-child"
    );

    expect(getKanbanCounters()).toEqual(["1", "1", "2"]);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(3)"
    );

    expect(getKanbanCounters()).toEqual(["0", "1", "3"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_save",
        "read_progress_bar",
        "web_resequence",
        "web_save",
        "read_progress_bar",
        "web_resequence",
        "web_save",
        "read_progress_bar",
        "web_resequence",
    ]);
});

test.tags("desktop");
test("d&d records grouped by date with progressbar with aggregates", async () => {
    Partner._records[0].date = "2010-11-30";
    Partner._records[1].date = "2010-11-30";
    Partner._records[2].date = "2010-10-30";
    Partner._records[3].date = "2010-10-30";

    // Usually kanban views grouped by a date, cannot drag and drop.
    // There are some overrides that allow the drag and drop of dates (CRM forecast for instance).
    // This patch is done to simulate these overrides.
    patchWithCleanup(KanbanRenderer.prototype, {
        isMovableField() {
            return true;
        },
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["date:month"],
    });

    expect(getKanbanCounters()).toEqual(["13", "19"]);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(getKanbanCounters()).toEqual(["-4", "36"]);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_save",
        "read_progress_bar",
        "formatted_read_group",
        "web_resequence",
    ]);
});

test("progress bar subgroup count recompute", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanCounters()).toEqual(["1", "3"]);

    await contains(".o_kanban_group:nth-child(2) .bg-success").click();

    expect(getKanbanCounters()).toEqual(["1", "1"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
    ]);
});

test.tags("desktop");
test("progress bar recompute after d&d to and from other column", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "1 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["1", "3"]);

    // Drag the last kanban record to the first column
    await contains(".o_kanban_group:last-child .o_kanban_record:nth-child(4)").dragAndDrop(
        ".o_kanban_group:first-child"
    );

    expect(getKanbanColumnTooltips()).toEqual(["1 gnap", "1 blip", "1 yop", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["2", "2"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_save",
        "read_progress_bar",
        "web_resequence",
    ]);
});

test("progress bar recompute after filter selection", async () => {
    Partner._records.push({ foo: "yop", bar: true, float_field: 100 });
    Partner._records.push({ foo: "yop", bar: true, float_field: 100 });
    Partner._records.push({ foo: "yop", bar: true, float_field: 100 });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My filter" domain="[['float_field', '=', 100]]"/>
            </search>`,
        groupBy: ["bar"],
    });

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "4 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["1", "6"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
    ]);

    await contains(".progress-bar.bg-success", { root: getKanbanColumn(1) }).click();

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "4 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["1", "4"]);
    expect.verifySteps(["web_search_read", "read_progress_bar"]);

    // Add search domain to something restricting progressbars' values (records still in filtered group)
    await toggleSearchBarMenu();
    await toggleMenuItem("My filter");

    expect(getKanbanColumnTooltips()).toEqual(["3 yop"]);
    expect(getKanbanCounters()).toEqual(["3"]);
    expect.verifySteps(["read_progress_bar", "web_read_group"]);
});

test("progress bar recompute after filter selection (aggregates)", async () => {
    Partner._records.push({ foo: "yop", bar: true, float_field: 100, int_field: 100 });
    Partner._records.push({ foo: "yop", bar: true, float_field: 100, int_field: 200 });
    Partner._records.push({ foo: "yop", bar: true, float_field: 100, int_field: 300 });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My filter" domain="[['float_field', '=', 100]]"/>
            </search>`,
        groupBy: ["bar"],
    });

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "4 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["-4", "636"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
    ]);

    await contains(".progress-bar.bg-success", { root: getKanbanColumn(1) }).click();

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "4 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["-4", "610"]);
    expect.verifySteps([
        "formatted_read_group", // recomputes aggregates
        "web_search_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
    ]);

    // Add searchdomain to something restricting progressbars' values (records still in filtered group)
    await toggleSearchBarMenu();
    await toggleMenuItem("My filter");

    expect(getKanbanColumnTooltips()).toEqual(["3 yop"]);
    expect(getKanbanCounters()).toEqual(["600"]);
    expect.verifySteps(["read_progress_bar", "web_read_group"]);
});

test("progress bar with monetary aggregate and multi currencies", async () => {
    const aed = {
        id: 3,
        name: "AED",
        symbol: "AED",
        position: "after",
        inverse_rate: 0.25,
        rate_date: "2017-03-17",
    };
    serverState.currencies = serverState.currencies.concat([aed]);
    Currency._records.push(aed);
    Partner._records.push({ id: 99, foo: "bar", salary: 300, currency_id: 3, product_id: 3 });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="salary"/>
                <field name="currency_id"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="salary"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_counter .o_animated_number").toHaveCount(2);
    expect(".o_kanban_counter:last .o_animated_number").toHaveText("$ 3,722");
    expect(".o_kanban_counter:first .o_animated_number").toHaveText("$ 4,050?");

    await toggleMultiCurrencyPopover(".o_kanban_counter:first .o_animated_number sup");
    expect(".o_multi_currency_popover").toHaveCount(1);
    expect(".o_multi_currency_popover").toHaveText(
        "8,100.00 € at $ 0.50 on Jun 13\n16,200.00 AED at $ 0.25 on Mar 17, 2017"
    );
});

test("progress bar with monetary aggregate and multi currencies: quick create record", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="salary"/>
            <field name="currency_id"/>
        </form>`;
    Partner._fields.currency_id.default = 1; // create new records in dollars by default
    Partner._records = [{ id: 99, foo: "bar", salary: 300, currency_id: 2, product_id: 3 }];
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban quick_create_view="some_view_ref">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="salary"/>
                <field name="currency_id"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="salary"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_counter .o_animated_number").toHaveCount(1);
    expect(".o_kanban_counter:last .o_animated_number").toHaveText("300 €");

    await quickCreateKanbanRecord();
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create .o_field_widget[name=currency_id] input").toHaveValue("USD");

    await editKanbanRecordQuickCreateInput("salary", 1000);
    await validateKanbanRecord();
    expect(".o_kanban_counter:last .o_animated_number").toHaveText("$ 1,300?");
});

test("progress bar with aggregates: activate bars (grouped by boolean)", async () => {
    Partner._records = [
        { foo: "yop", bar: true, int_field: 1 },
        { foo: "yop", bar: true, int_field: 2 },
        { foo: "blip", bar: true, int_field: 4 },
        { foo: "gnap", bar: true, int_field: 8 },
    ];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanColumnTooltips(0)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["15"]);

    await contains(getKanbanProgressBars(0)[0]).click();
    expect(getKanbanCounters()).toEqual(["3"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["4"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["15"]);
});

test("progress bar with aggregates: activate bars (grouped by many2one)", async () => {
    Partner._records = [
        { foo: "yop", product_id: 3, int_field: 1 },
        { foo: "yop", product_id: 3, int_field: 2 },
        { foo: "blip", product_id: 3, int_field: 4 },
        { foo: "gnap", product_id: 3, int_field: 8 },
    ];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="float_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    onRpc("partner", "web_read_group", ({ kwargs }) => {
        // float_field is not in the progressbar, then never ask his aggregation
        expect(kwargs.aggregates).not.toInclude("float_field:sum");
    });

    expect(getKanbanColumnTooltips(0)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["15"]);

    await contains(getKanbanProgressBars(0)[0]).click();
    expect(getKanbanCounters()).toEqual(["3"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["4"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["15"]);
});

test("progress bar with aggregates: activate bars (grouped by date)", async () => {
    Partner._records = [
        { foo: "yop", date: "2023-10-08", int_field: 1 },
        { foo: "yop", date: "2023-10-08", int_field: 2 },
        { foo: "blip", date: "2023-10-08", int_field: 4 },
        { foo: "gnap", date: "2023-10-08", int_field: 8 },
    ];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["date:week"],
    });

    expect(getKanbanColumnTooltips(0)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["15"]);

    await contains(getKanbanProgressBars(0)[0]).click();
    expect(getKanbanCounters()).toEqual(["3"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["4"]);

    await contains(getKanbanProgressBars(0)[2]).click();
    expect(getKanbanCounters()).toEqual(["15"]);
});

test("progress bar with aggregates: Archive all in a column", async () => {
    Partner._fields.active = fields.Boolean({ default: true });
    Partner._records = [
        { foo: "yop", bar: true, int_field: 1, active: true },
        { foo: "yop", bar: true, int_field: 2, active: true },
        { foo: "blip", bar: true, int_field: 4, active: true },
        { foo: "gnap", bar: true, int_field: 8, active: true },
        { foo: "oups", bar: false, int_field: 268, active: true },
    ];

    let def;
    onRpc("web_read_group", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates><t t-name="card">
                        <field name="foo"/>
                </t></templates>
            </kanban>`,
        groupBy: ["bar"],
        loadActionMenus: true,
    });

    expect(getKanbanColumnTooltips(1)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["268", "15"]);
    await keyDown("alt");
    await animationFrame();
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(1)").click();
    await keyUp("alt");
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(2)").click();
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(3)").click();
    await contains(".o_kanban_group:nth-of-type(2) .o_kanban_record:nth-of-type(4)").click();
    await contains(".o_cp_action_menus button").click();
    await contains(".o_menu_item:contains(Archive)").click();
    expect(".o_dialog").toHaveCount(1);
    def = new Deferred();
    await contains(".modal-footer .btn-primary").click();
    expect(getKanbanColumnTooltips(1)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["268", "15"]);
    def.resolve();
    await animationFrame();
    expect(getKanbanColumnTooltips(1)).toEqual([]);
    expect(getKanbanCounters()).toEqual(["268", "0"]);
});

test.tags("desktop");
test("column progressbars on quick create with quick_create_view", async () => {
    Partner._views["form,some_view_ref"] = `<form><field name="int_field"/></form>`;

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanCounters()).toEqual(["-4", "36"]);

    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("int_field", 44);
    await validateKanbanRecord();

    expect(getKanbanCounters()).toEqual(["40", "36"], {
        message: "kanban counters should have been updated on quick create",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "get_views",
        "onchange",
        "web_save",
        "onchange",
        "web_read",
        "read_progress_bar",
        "formatted_read_group",
    ]);
});

test.tags("desktop");
test("progressbars and active filter with quick_create_view", async () => {
    Partner._views["form,some_view_ref"] = `
        <form>
            <field name="int_field"/>
            <field name="foo"/>
        </form>`;

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await contains(".progress-bar.bg-danger", { root: getKanbanColumn(0) }).click();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".oe_kanban_card_danger", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(getKanbanCounters()).toEqual(["-4", "36"]);

    // open the quick create
    createKanbanRecord();
    await animationFrame();

    // fill it with a record that satisfies the active filter
    await editKanbanRecordQuickCreateInput("int_field", 44);
    await editKanbanRecordQuickCreateInput("foo", "blip");
    await contains(".o_kanban_quick_create .o_kanban_add").click();

    // fill it again with another record that DOES NOT satisfy the active filter
    await editKanbanRecordQuickCreateInput("int_field", 1000);
    await editKanbanRecordQuickCreateInput("foo", "yop");
    await contains(".o_kanban_quick_create .o_kanban_add").click();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(3);
    expect(queryAll(".oe_kanban_card_danger", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(queryAll(".oe_kanban_card_success", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(getKanbanCounters()).toEqual(["40", "36"], {
        message:
            "kanban counters should have been updated on quick create, respecting the active filter",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "formatted_read_group",
        "web_search_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
        "get_views",
        "onchange",
        "web_save",
        "onchange",
        "web_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
        "web_save",
        "onchange",
        "web_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
    ]);
});

test("progressbar filter state is kept unchanged when domain is updated (records still in group)", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[['foo', '=', 'yop']]"/>
            </search>`,
    });

    // Check that we have 2 columns and check their progressbar's state
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);

    // Apply an active filter
    await contains(".o_kanban_group:nth-child(2) .progress-bar.bg-success").click();

    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);

    // Add searchdomain to something restricting progressbars' values (records still in filtered group)
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");

    // Check that we have now 1 column only and check its progressbar's state
    expect(".o_kanban_group").toHaveCount(1);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["Yes"]);
    expect(getKanbanColumnTooltips()).toEqual(["1 yop"]);

    // Undo searchdomain
    await toggleMenuItem("My Filter");

    // Check that we have 2 columns back and check their progressbar's state
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "read_progress_bar",
        "web_read_group",
        "read_progress_bar",
        "web_read_group",
    ]);
});

test("progressbar filter state is kept unchanged when domain is updated (emptying group)", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="id"/>
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[['foo', '=', 'blip']]"/>
            </search>`,
    });

    // Check that we have 2 columns, check their progressbar's state and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop", "2blip", "3gnap"]);

    // Apply an active filter
    await contains(".o_kanban_group:nth-child(2) .progress-bar.bg-success").click();

    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop"]);

    // Add searchdomain to something restricting progressbars' values + emptying the filtered group
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");

    // Check that we still have 2 columns, check their progressbar's state and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(1)).toEqual(["2blip"]);

    // Undo searchdomain
    await toggleMenuItem("My Filter");

    // Check that we still have 2 columns and check their progressbar's state
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop", "2blip", "3gnap"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
    ]);
});

test.tags("desktop");
test("filtered column counters when dropping in non-matching record", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="id"/>
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    // Check that we have 2 columns, check their progressbar's state, and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop", "2blip", "3gnap"]);

    // Apply an active filter
    await contains(".o_kanban_group:nth-child(2) .progress-bar.bg-success").click();

    expect(getKanbanColumn(1)).toHaveClass("o_kanban_group_show");
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(".o_kanban_group.o_kanban_group_show .o_kanban_record").toHaveCount(1);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop"]);

    // Drop in the non-matching record from first column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        queryFirst(".o_kanban_group.o_kanban_group_show")
    );

    // Check that we have 2 columns, check their progressbar's state, and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual([]);
    expect(getKanbanRecordTexts(0)).toEqual([]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "2 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop", "4blip"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "web_save",
        "read_progress_bar",
        "web_resequence",
    ]);
});

test.tags("desktop");
test("filtered column is reloaded when dragging out its last record", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="id"/>
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    // Check that we have 2 columns, check their progressbar's state, and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop", "2blip", "3gnap"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
    ]);

    // Apply an active filter
    await contains(".o_kanban_group:nth-child(2) .progress-bar.bg-success").click();

    expect(getKanbanColumn(1)).toHaveClass("o_kanban_group_show");
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(1);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(".o_kanban_group.o_kanban_group_show .o_kanban_record").toHaveCount(1);
    expect(getKanbanRecordTexts(1)).toEqual(["1yop"]);
    expect.verifySteps(["web_search_read", "read_progress_bar"]);

    // Drag out its only record onto the first column
    await contains(".o_kanban_group.o_kanban_group_show .o_kanban_record").dragAndDrop(
        queryFirst(".o_kanban_group:first-child")
    );

    // Check that we have 2 columns, check their progressbar's state, and check records
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group.o_kanban_group_show").toHaveCount(0);
    expect(queryAllTexts(".o_column_title")).toEqual(["No", "Yes"]);
    expect(getKanbanColumnTooltips(0)).toEqual(["1 yop", "1 blip"]);
    expect(getKanbanRecordTexts(0)).toEqual(["4blip", "1yop"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 blip", "1 Other"]);
    expect(getKanbanRecordTexts(1)).toEqual(["2blip", "3gnap"]);
    expect.verifySteps(["web_save", "read_progress_bar", "web_search_read", "web_resequence"]);
});

test.tags("desktop");
test("filter groups kept when leaving/coming back", async () => {
    Partner._records[1].state = "abc";
    Partner._views = {
        kanban: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <t t-name="card">
                        <field name="id" />
                    </t>
                </templates>
            </kanban>`,
        form: `
            <form>
                <field name="state" widget="radio"/>
            </form>`,
    };
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
        context: {
            group_by: ["bar"],
        },
    });

    // Filter on state "abc" => matches 2 records
    await contains(getKanbanProgressBars(1)[0]).click();
    expect(getKanbanRecordTexts(0)).toEqual(["4"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1", "2"]);

    // open a record
    await contains(getKanbanRecord({ index: 1 })).click();
    expect(".o_form_view").toHaveCount(1);

    // go back to kanban view
    await contains(".breadcrumb-item a").click();
    expect(getKanbanRecordTexts(0)).toEqual(["4"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1", "2"]);

    // open a record
    await contains(getKanbanRecord({ index: 1 })).click();
    expect(".o_form_view").toHaveCount(1);

    // select another state
    await contains(queryAll("input.o_radio_input")[1]).click();
    // go back to kanban view
    await contains(".breadcrumb-item a").click();
    expect(getKanbanRecordTexts(0)).toEqual(["4"]);
    expect(getKanbanRecordTexts(1)).toEqual(["2"]);
});

test("Color '200' (gray) can be used twice (for false value and another value) in progress bar", async () => {
    Partner._records.push({ id: 5, bar: true }, { id: 6, bar: false });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "200", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="state"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group:nth-child(1) .progress-bar").toHaveCount(2);
    expect(
        queryAll(".o_kanban_group:nth-child(1) .progress-bar").map((el) => el.dataset.tooltip)
    ).toEqual(["1 blip", "1 Other"]);
    expect(".o_kanban_group:nth-child(2) .progress-bar").toHaveCount(4);
    expect(
        queryAll(".o_kanban_group:nth-child(2) .progress-bar").map((el) => el.dataset.tooltip)
    ).toEqual(["1 yop", "1 gnap", "1 blip", "1 Other"]);
    expect(getKanbanCounters()).toEqual(["2", "4"]);

    await contains(".o_kanban_group:nth-child(2) .progress-bar").click();

    expect(getKanbanCounters()).toEqual(["2", "1"]);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveText("ABC");
    expect(".o_kanban_group:nth-child(2) .o_kanban_load_more").toHaveCount(0);

    await contains(".o_kanban_group:nth-child(2) .progress-bar:nth-child(2)").click();

    expect(getKanbanCounters()).toEqual(["2", "1"]);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveText("GHI");
    expect(".o_kanban_group:nth-child(2) .o_kanban_load_more").toHaveCount(0);

    await contains(".o_kanban_group:nth-child(2) .progress-bar:nth-child(4)").click();

    expect(getKanbanCounters()).toEqual(["2", "1"]);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveText("");
    expect(".o_kanban_group:nth-child(2) .o_kanban_load_more").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "web_search_read",
        "read_progress_bar",
        "web_search_read",
        "read_progress_bar",
    ]);
});

test("update field on which progress bars are computed", async () => {
    Partner._records.push({ id: 5, state: "abc", bar: true });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <div t-name="card">
                        <field name="state" widget="state_selection" />
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // Initial state: 2 columns, the "Yes" column contains 2 records "abc", 1 "def" and 1 "ghi"
    expect(getKanbanCounters()).toEqual(["1", "4"]);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(4);
    expect(queryAll(".o_column_progress .progress-bar", { root: getKanbanColumn(1) })).toHaveCount(
        3
    );
    expect(getKanbanProgressBars(1)[0].style.width).toBe("50%"); // abc: 2
    expect(getKanbanProgressBars(1)[1].style.width).toBe("25%"); // def: 1
    expect(getKanbanProgressBars(1)[2].style.width).toBe("25%"); // ghi: 1

    // Filter on state "abc" => matches 2 records
    await contains(getKanbanProgressBars(1)[0]).click();

    expect(getKanbanCounters()).toEqual(["1", "2"]);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(queryAll(".o_column_progress .progress-bar", { root: getKanbanColumn(1) })).toHaveCount(
        3
    );
    expect(getKanbanProgressBars(1)[0].style.width).toBe("50%"); // abc: 2
    expect(getKanbanProgressBars(1)[1].style.width).toBe("25%"); // def: 1
    expect(getKanbanProgressBars(1)[2].style.width).toBe("25%"); // ghi: 1

    // Changes the state of the first record of the "Yes" column to "def"
    // The updated record should remain visible
    await contains(".o_status", { root: getKanbanRecord({ index: 2 }) }).click();
    await contains(".o-dropdown-item:nth-child(2)", {
        root: getDropdownMenu(getKanbanRecord({ index: 2 })),
    }).click();

    expect(getKanbanCounters()).toEqual(["1", "1"]);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(queryAll(".o_column_progress .progress-bar", { root: getKanbanColumn(1) })).toHaveCount(
        3
    );
    expect(getKanbanProgressBars(1)[0].style.width).toBe("25%"); // abc: 1
    expect(getKanbanProgressBars(1)[1].style.width).toBe("50%"); // def: 2
    expect(getKanbanProgressBars(1)[2].style.width).toBe("25%"); // ghi: 1

    // Filter on state "def" => matches 2 records (including the one we just changed)
    await contains(getKanbanProgressBars(1)[1]).click();

    expect(getKanbanCounters()).toEqual(["1", "2"]);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(getKanbanProgressBars(1)[0].style.width).toBe("25%"); // abc: 1
    expect(getKanbanProgressBars(1)[1].style.width).toBe("50%"); // def: 2
    expect(getKanbanProgressBars(1)[2].style.width).toBe("25%"); // ghi: 1

    // Filter back on state "abc" => matches only 1 record
    await contains(getKanbanProgressBars(1)[0]).click();

    expect(getKanbanCounters()).toEqual(["1", "1"]);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(1);
    expect(getKanbanProgressBars(1)[0].style.width).toBe("25%"); // abc: 1
    expect(getKanbanProgressBars(1)[1].style.width).toBe("50%"); // def: 2
    expect(getKanbanProgressBars(1)[2].style.width).toBe("25%"); // ghi: 1
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_search_read",
        "read_progress_bar",
        "web_save",
        "read_progress_bar",
        "web_search_read",
        "read_progress_bar",
        "web_search_read",
        "read_progress_bar",
    ]);
});

test("load more button shouldn't be visible when unfiltering column", async () => {
    Partner._records.push({ id: 5, state: "abc", bar: true });

    let def;
    onRpc("web_search_read", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <div t-name="card">
                        <field name="state" widget="state_selection" />
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    // Initial state: 2 columns, the "No" column contains 1 record, The "Yes" column contains 4 records
    expect(getKanbanCounters()).toEqual(["1", "4"]);

    // Filter on state "abc" => matches 2 records
    await contains(getKanbanProgressBars(1)[0]).click();

    // Filtered state: 2 columns, the "No" column contains 1 record, The "Yes" column contains 2 records
    expect(getKanbanCounters()).toEqual(["1", "2"]);

    def = new Deferred();
    // UnFiltered the "Yes" column
    await contains(getKanbanProgressBars(1)[0]).click();
    expect(".o_kanban_load_more").toHaveCount(0, {
        message: "The load more button should not be visible",
    });

    def.resolve();
    await animationFrame();

    // Return to initial state
    expect(getKanbanCounters()).toEqual(["1", "4"]);
    expect(".o_kanban_load_more").toHaveCount(0, {
        message: "The load more button should not be visible",
    });
});

test("click on the progressBar of a new column", async () => {
    Partner._records = [];

    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.domain).toEqual([
            "&",
            "&",
            ["id", ">", 0],
            ["product_id", "=", 6],
            "!",
            ["state", "in", ["abc", "def", "ghi"]],
        ]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id" on_create="quick_create">
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <div t-name="card">
                        <field name="state" widget="state_selection" />
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        domain: [["id", ">", 0]],
    });

    // Create a new column
    await editKanbanColumnName("new column");
    await validateKanbanColumn();

    // Crete a record in the new column
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "new product");
    await validateKanbanRecord();

    expect(".o_kanban_record").toHaveCount(1);

    // Togggle the progressBar
    await contains(getKanbanProgressBars(0)[0]).click();

    expect(".o_kanban_record").toHaveCount(1);
    expect.verifySteps(["web_search_read"]);
});

test.tags("desktop");
test("drag record to folded column, with progressbars", async () => {
    Partner._records[0].bar = false;

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field" />
                <templates>
                    <div t-name="card">
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(getKanbanProgressBars(0).map((pb) => pb.style.width)).toEqual(["50%", "50%"]);
    expect(getKanbanProgressBars(1).map((pb) => pb.style.width)).toEqual(["50%", "50%"]);
    expect(getKanbanCounters()).toEqual(["6", "26"]);

    const clickColumnAction = await toggleKanbanColumnActions(1);
    clickColumnAction("Fold");
    await animationFrame();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(queryText(getKanbanColumn(1))).toBe("Yes\n(2)");

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryText(getKanbanColumn(1))).toBe("Yes\n(3)");
    expect(getKanbanProgressBars(0).map((pb) => pb.style.width)).toEqual(["100%"]);
    expect(getKanbanCounters()).toEqual(["-4"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "has_group",
        "web_save",
        "read_progress_bar",
        "formatted_read_group",
    ]);
});

test.tags("desktop");
test("scroll on group unfold and progressbar click", async () => {
    Product._records[1].fold = true;
    onRpc(function ({ method, parent }) {
        expect.step(method);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field" />
                <templates>
                    <t t-name="card">Record</t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect.verifySteps(["get_views", "read_progress_bar", "web_read_group", "has_group"]);
    queryOne(".o_content").style.maxHeight = "80px";
    on(".o_content", "scroll", () => expect.step("scrolled"));

    await scroll(".o_content", { top: 50 }); // scroll down to allow auto-scroll to top
    await contains(getKanbanProgressBars(0)[0]).click();

    expect.verifySteps([
        "scrolled",
        "formatted_read_group",
        "web_search_read",
        "read_progress_bar",
        "formatted_read_group",
        "formatted_read_group",
    ]);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");

    await scroll(".o_content", { top: 50 }); // scroll down to allow auto-scroll to top
    await contains(getKanbanColumn(1)).click();

    expect.verifySteps(["scrolled", "web_search_read"]);
});

test("searchbar filters are displayed directly (with progressbar)", async () => {
    let def;
    onRpc("read_progress_bar", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["int_field"],
        searchViewArch: `
            <search>
                <filter name="some_filter" string="Some Filter" domain="[['foo', '!=', 'bar']]"/>
            </search>`,
    });

    expect(getFacetTexts()).toEqual([]);

    // toggle a filter, and slow down the read_progress_bar rpc
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");

    expect(getFacetTexts()).toEqual(["Some Filter"]);

    def.resolve();
    await animationFrame();
    expect(getFacetTexts()).toEqual(["Some Filter"]);
});

test("Correct values for progress bar with toggling filter and slow RPC", async () => {
    let def;
    onRpc("read_progress_bar", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        searchViewArch: `
            <search>
                <filter name="some_filter" string="Some Filter" domain="[['state', '!=', 'ghi']]"/>
            </search>`,
    });

    expect(".o_kanban_record").toHaveCount(4);
    // abc: 1, ghi: 1
    expect(getKanbanProgressBars(1).map((pb) => pb.style.width)).toEqual(["50%", "50%"]);

    // toggle a filter, and slow down the read_progress_bar rpc
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");
    // abc: 1, ghi: 1
    expect(getKanbanProgressBars(1).map((pb) => pb.style.width)).toEqual(["50%", "50%"]);

    def.resolve();
    await animationFrame();
    // After the call to read_progress_bar has resolved, the values should be updated correctly
    expect(".o_kanban_record").toHaveCount(2);
    // abc: 1
    expect(getKanbanProgressBars(1).map((pb) => pb.style.width)).toEqual(["100%"]);
});
