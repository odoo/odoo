import { after, beforeEach, expect, test } from "@odoo/hoot";
import {
    click,
    dblclick,
    drag,
    edit,
    hover,
    leave,
    pointerDown,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryText,
    resize,
    setInputFiles,
} from "@odoo/hoot-dom";
import { Deferred, advanceFrame, animationFrame, runAllTimers, tick } from "@odoo/hoot-mock";
import { Component, onRendered, onWillRender, xml } from "@odoo/owl";
import {
    MockServer,
    clickKanbanLoadMore,
    clickModalButton,
    contains,
    createKanbanRecord,
    defineModels,
    defineParams,
    discardKanbanRecord,
    editKanbanColumnName,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    fields,
    getDropdownMenu,
    getFacetTexts,
    getKanbanColumn,
    getKanbanColumnDropdownMenu,
    getKanbanColumnTooltips,
    getKanbanCounters,
    getKanbanProgressBars,
    getKanbanRecord,
    getKanbanRecordTexts,
    getPagerLimit,
    getPagerValue,
    getService,
    makeServerError,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    pagerNext,
    pagerPrevious,
    patchWithCleanup,
    quickCreateKanbanColumn,
    quickCreateKanbanRecord,
    serverState,
    stepAllNetworkCalls,
    toggleKanbanColumnActions,
    toggleKanbanRecordDropdown,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
    validateKanbanColumn,
    validateKanbanRecord,
    validateSearch,
    webModels,
} from "@web/../tests/web_test_helpers";
import { FileInput } from "@web/core/file_input/file_input";

import { currencies } from "@web/core/currency";
import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { SampleServer } from "@web/model/sample_server";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ViewButton } from "@web/views/view_button/view_button";
import { AnimatedNumber } from "@web/views/view_components/animated_number";
import { WebClient } from "@web/webclient/webclient";
import { browser } from "@web/core/browser/browser";

const { IrAttachment } = webModels;

const fieldRegistry = registry.category("fields");
const viewRegistry = registry.category("views");
const viewWidgetRegistry = registry.category("view_widgets");

async function createFileInput({ mockPost, mockAdd, props }) {
    mockService("notification", {
        add: mockAdd || (() => {}),
    });
    mockService("http", {
        post: mockPost || (() => {}),
    });
    await mountWithCleanup(FileInput, { props });
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
    salary = fields.Monetary({ aggregator: "sum", currency_field: this.currency_id });
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

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
    ];
}

defineModels([Partner, Product, Category, Currency, IrAttachment]);

beforeEach(() => {
    patchWithCleanup(AnimatedNumber, { enableAnimations: false });
});

test("basic ungrouped rendering", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.context.bin_size).toBe(true);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`,
    });

    expect(".o_kanban_view").toHaveClass("o_kanban_test");
    expect(".o_kanban_renderer").toHaveClass("o_kanban_ungrouped");
    expect(".o_control_panel_main_buttons button.o-kanban-button-new").toHaveCount(1);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);
    expect(".o_kanban_ghost").toHaveCount(6);
    expect(".o_kanban_record:contains(gnap)").toHaveCount(1);
});

test("kanban rendering with class and style attributes", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="myCustomClass" style="border: 1px solid red;">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect("[style*='border: 1px solid red;']").toHaveCount(0, {
        message: "style attribute should not be copied",
    });
    expect(".o_view_controller.o_kanban_view.myCustomClass").toHaveCount(1, {
        message: "class attribute should be passed to the view controller",
    });
    expect(".myCustomClass").toHaveCount(1, {
        message: "class attribute should ONLY be passed to the view controller",
    });
});

test("generic tags are case insensitive", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <Div class="test">Hello</Div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("div.test").toHaveCount(4);
});

test("kanban records are clickable by default", async () => {
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
        selectRecord: (resId) => {
            expect(resId).toBe(1, { message: "should trigger an event to open the form view" });
        },
    });

    await contains(".o_kanban_record").click();
});

test("kanban records with global_click='0'", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban can_open="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect.step("select record");
        },
    });

    await contains(".o_kanban_record").click();
    expect.verifySteps([]);
});

test("float fields are formatted properly without using a widget", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="float_field" digits="[0,5]"/>
                        <field name="float_field" digits="[0,3]"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:first").toHaveText("0.40000\n0.400");
});

test("field with widget and attributes in kanban", async () => {
    const myField = {
        component: class MyField extends Component {
            static template = xml`<span/>`;
            static props = ["*"];
            setup() {
                if (this.props.record.resId === 1) {
                    expect(this.props.attrs).toEqual({
                        name: "int_field",
                        widget: "my_field",
                        str: "some string",
                        bool: "true",
                        num: "4.5",
                        field_id: "int_field_0",
                    });
                }
            }
        },
        extractProps: ({ attrs }) => ({ attrs }),
    };
    fieldRegistry.add("my_field", myField);
    after(() => fieldRegistry.remove("my_field"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <field name="int_field" widget="my_field"
                            str="some string"
                            bool="true"
                            num="4.5"
                        />
                    </t>
                </templates>
            </kanban>`,
    });
});

test("kanban with integer field with human_readable option", async () => {
    Partner._records[0].int_field = 5 * 1000 * 1000;
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field" options="{'human_readable': true}"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["5M", "9", "17", "-4"]);
    expect(".o_field_widget").toHaveCount(0);
});

test.tags("desktop");
test("Hide tooltip when user click inside a kanban headers item", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id">
                <field name="product_id" options='{"group_by_tooltip": {"name": "Name"}}'/>
                <templates>
                    <t t-name="card"/>
                </templates>
            </kanban>`,
    });
    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_column_title").toHaveCount(2);
    expect(".o-tooltip").toHaveCount(0);

    await hover(".o_kanban_group:first-child .o_kanban_header_title .o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(1);

    await contains(
        ".o_kanban_group:first-child .o_kanban_header_title .o_kanban_quick_add"
    ).click();
    expect(".o-tooltip").toHaveCount(0);

    await hover(".o_kanban_group:first-child .o_kanban_header_title .o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(1);

    await contains(".o_kanban_group:first-child .o_kanban_header_title .fa-gear", {
        visible: false,
    }).click();
    expect(".o-tooltip").toHaveCount(0);
});

test.tags("desktop");
test("basic grouped rendering", async () => {
    expect.assertions(16);

    patchWithCleanup(KanbanRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            onRendered(() => {
                expect.step("rendered");
            });
        },
    });

    onRpc("web_read_group", ({ kwargs }) => {
        // the lazy option is important, so the server can fill in the empty groups
        expect(kwargs.lazy).toBe(true, { message: "should use lazy read_group" });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(".o_kanban_view").toHaveClass("o_kanban_test");
    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_control_panel_main_buttons button.o-kanban-button-new").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect.verifySteps(["rendered"]);

    await toggleKanbanColumnActions(0);

    // check available actions in kanban header's config dropdown
    expect(".o-dropdown--menu .o_kanban_toggle_fold").toHaveCount(1);
    expect(".o_kanban_header:first-child .o_kanban_config .o_column_edit").toHaveCount(0);
    expect(".o_kanban_header:first-child .o_kanban_config .o_column_delete").toHaveCount(0);
    expect(".o_kanban_header:first-child .o_kanban_config .o_column_archive_records").toHaveCount(
        0
    );
    expect(".o_kanban_header:first-child .o_kanban_config .o_column_unarchive_records").toHaveCount(
        0
    );

    // focuses the search bar and closes the dropdown
    await click(".o_searchview input");

    // the next line makes sure that reload works properly.  It looks useless,
    // but it actually test that a grouped local record can be reloaded without
    // changing its result.
    await validateSearch();
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect.verifySteps(["rendered"]);
});

test("basic grouped rendering with no record", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });
    expect(".o_kanban_grouped").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_control_panel_main_buttons button.o-kanban-button-new").toHaveCount(1, {
        message:
            "There should be a 'New' button even though there is no column when groupby is not a many2one",
    });
});

test("grouped rendering with active field (archivable by default)", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

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

    const clickColumnAction = await toggleKanbanColumnActions(1);

    // check archive/restore all actions in kanban header's config dropdown
    expect(".o_column_archive_records").toHaveCount(1, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_column_unarchive_records").toHaveCount(1, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3);

    await clickColumnAction("Archive All");
    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(0);
});

test("grouped rendering with active field (archivable true)", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban archivable="true">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    const clickColumnAction = await toggleKanbanColumnActions(0);

    // check archive/restore all actions in kanban header's config dropdown
    expect(".o_column_archive_records").toHaveCount(1, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_column_unarchive_records").toHaveCount(1, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3);

    await clickColumnAction("Archive All");
    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(0);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3);
});

test.tags("desktop");
test("empty group when grouped by date", async () => {
    Partner._records[0].date = "2017-01-08";
    Partner._records[1].date = "2017-02-09";
    Partner._records[2].date = "2017-02-08";
    Partner._records[3].date = "2017-02-10";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`,
        groupBy: ["date:month"],
    });

    expect(queryAllTexts(".o_kanban_header")).toEqual(["January 2017\n(1)", "February 2017\n(3)"]);

    Partner._records.shift(); // remove only record of the first group

    await press("Enter"); // reload
    await animationFrame();

    expect(queryAllTexts(".o_kanban_header")).toEqual(["January 2017\n(0)", "February 2017\n(3)"]);

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(0);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3);
});

test("grouped rendering with active field (archivable false)", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban archivable="false">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    await toggleKanbanColumnActions(0);

    // check archive/restore all actions in kanban header's config dropdown
    expect(".o_column_archive_records").toHaveCount(0, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_column_unarchive_records").toHaveCount(0, { root: getKanbanColumnDropdownMenu(0) });
});

test.tags("desktop");
test("m2m grouped rendering with active field (archivable true)", async () => {
    // add active field on partner model and make all records active
    Partner._fields.active = fields.Boolean({ default: true });

    // more many2many data
    Partner._records[0].category_ids = [6, 7];
    Partner._records[3].foo = "blork";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban archivable="true">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["category_ids"],
    });

    expect(".o_kanban_group").toHaveCount(3);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(2) })).toHaveCount(2);

    expect(queryAllTexts(".o_kanban_group")).toEqual([
        "None\n(1)",
        "gold\n(2)\nyop\nblip",
        "silver\n(2)\nyop\ngnap",
    ]);

    await click(getKanbanColumn(0));
    await animationFrame();
    await toggleKanbanColumnActions(0);

    // check archive/restore all actions in kanban header's config dropdown
    // despite the fact that the kanban view is configured to be archivable,
    // the actions should not be there as it is grouped by an m2m field.
    expect(".o_column_archive_records").toHaveCount(0, { root: getKanbanColumnDropdownMenu(0) });
    expect(".o_column_unarchive_records").toHaveCount(0, { root: getKanbanColumnDropdownMenu(0) });
});

test("kanban grouped by date field", async () => {
    Partner._records[0].date = "2007-06-10";

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
        groupBy: ["date"],
    });

    expect(queryAllTexts(".o_column_title")).toEqual(["None\n(3)", "June 2007\n(1)"]);
});

test("context can be used in kanban template", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field t-if="context.some_key" name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        context: { some_key: 1 },
        domain: [["id", "=", 1]],
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span:contains(yop)").toHaveCount(1);
});

test("kanban with sub-template", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <t t-call="another-template"/>
                    </t>
                    <t t-name="another-template">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "yop",
        "blip",
        "gnap",
        "blip",
    ]);
});

test("kanban with t-set outside card", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="int_field"/>
                <templates>
                    <t t-name="card">
                        <t t-set="x" t-value="record.int_field.value"/>
                        <div>
                            <t t-esc="x"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["10", "9", "17", "-4"]);
});

test("kanban with t-if/t-else on field", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field t-if="record.int_field.value > -1" name="int_field"/>
                        <t t-else="">Negative value</t>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "10",
        "9",
        "17",
        "Negative value",
    ]);
});

test("kanban with t-if/t-else on field with widget", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field t-if="record.int_field.value > -1" name="int_field" widget="integer"/>
                        <t t-else="">Negative value</t>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "10",
        "9",
        "17",
        "Negative value",
    ]);
});

test("field with widget and dynamic attributes in kanban", async () => {
    const myField = {
        component: class MyField extends Component {
            static template = xml`<span/>`;
            static props = ["*"];
        },
        extractProps: ({ attrs }) => {
            expect.step(
                `${attrs["dyn-bool"]}/${attrs["interp-str"]}/${attrs["interp-str2"]}/${attrs["interp-str3"]}`
            );
        },
    };
    fieldRegistry.add("my_field", myField);
    after(() => fieldRegistry.remove("my_field"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <field name="int_field" widget="my_field"
                            t-att-dyn-bool="record.foo.value.length > 3"
                            t-attf-interp-str="hello {{record.foo.value}}"
                            t-attf-interp-str2="hello #{record.foo.value} !"
                            t-attf-interp-str3="hello {{record.foo.value}} }}"
                        />
                    </t>
                </templates>
            </kanban>`,
    });
    expect.verifySteps([
        "false/hello yop/hello yop !/hello yop }}",
        "true/hello blip/hello blip !/hello blip }}",
        "true/hello gnap/hello gnap !/hello gnap }}",
        "true/hello blip/hello blip !/hello blip }}",
    ]);
});

test("view button and string interpolated attribute in kanban", async () => {
    patchWithCleanup(ViewButton.prototype, {
        setup() {
            super.setup();
            expect.step(`[${this.props.clickParams["name"]}] className: '${this.props.className}'`);
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <a name="one" type="object" class="hola"/>
                        <a name="two" type="object" class="hola" t-attf-class="hello"/>
                        <a name="sri" type="object" class="hola" t-attf-class="{{record.foo.value}}"/>
                        <a name="foa" type="object" class="hola" t-attf-class="{{record.foo.value}} olleh"/>
                        <a name="fye" type="object" class="hola" t-attf-class="hello {{record.foo.value}}"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect.verifySteps([
        "[one] className: 'hola oe_kanban_action'",
        "[two] className: 'hola oe_kanban_action hello'",
        "[sri] className: 'hola oe_kanban_action yop'",
        "[foa] className: 'hola oe_kanban_action yop olleh'",
        "[fye] className: 'hola oe_kanban_action hello yop'",
        "[one] className: 'hola oe_kanban_action'",
        "[two] className: 'hola oe_kanban_action hello'",
        "[sri] className: 'hola oe_kanban_action blip'",
        "[foa] className: 'hola oe_kanban_action blip olleh'",
        "[fye] className: 'hola oe_kanban_action hello blip'",
        "[one] className: 'hola oe_kanban_action'",
        "[two] className: 'hola oe_kanban_action hello'",
        "[sri] className: 'hola oe_kanban_action gnap'",
        "[foa] className: 'hola oe_kanban_action gnap olleh'",
        "[fye] className: 'hola oe_kanban_action hello gnap'",
        "[one] className: 'hola oe_kanban_action'",
        "[two] className: 'hola oe_kanban_action hello'",
        "[sri] className: 'hola oe_kanban_action blip'",
        "[foa] className: 'hola oe_kanban_action blip olleh'",
        "[fye] className: 'hola oe_kanban_action hello blip'",
    ]);
});

test("pager should be hidden in grouped mode", async () => {
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

    expect(".o_pager").toHaveCount(0);
});

test("there should be no limit on the number of fetched groups", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_GROUP_LIMIT: 1 });

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
    });

    expect(".o_kanban_group").toHaveCount(2);
});

test("pager, ungrouped, with default limit", async () => {
    expect.assertions(2);

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.limit).toBe(40);
    });

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
    });

    expect(".o_pager").toHaveCount(1);
});

test.tags("desktop");
test("pager, ungrouped, with default limit on desktop", async () => {
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
    });

    expect(getPagerValue()).toEqual([1, 4]);
});

test("pager, ungrouped, with limit given in options", async () => {
    expect.assertions(1);

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.limit).toBe(2);
    });

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
        limit: 2,
    });
});

test.tags("desktop");
test("pager, ungrouped, with limit given in options on desktop", async () => {
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
        limit: 2,
    });
    expect(getPagerValue()).toEqual([1, 2]);
    expect(getPagerLimit()).toBe(4);
});

test("pager, ungrouped, with limit set on arch and given in options", async () => {
    expect.assertions(1);

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.limit).toBe(3);
    });

    // the limit given in the arch should take the priority over the one given in options
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        limit: 2,
    });
});

test.tags("desktop");
test("pager, ungrouped, with limit set on arch and given in options on desktop", async () => {
    // the limit given in the arch should take the priority over the one given in options
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        limit: 2,
    });

    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(4);
});

test.tags("desktop");
test("pager, ungrouped, with count limit reached", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    stepAllNetworkCalls();

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
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_pager_limit").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("4");
    expect.verifySteps(["search_count"]);
});

test("pager, ungrouped, with count limit reached, click next", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    stepAllNetworkCalls();

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
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_pager_next").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect.verifySteps(["web_search_read"]);
});

test.tags("desktop");
test("pager, ungrouped, with count limit reached, click next on desktop", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

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
    });

    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");

    await contains(".o_pager_next").click();

    expect(".o_pager_value").toHaveText("3-4");
    expect(".o_pager_limit").toHaveText("4");
});

test("pager, ungrouped, with count limit reached, click next (2)", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    Partner._records.push({ id: 5, foo: "xxx" });

    stepAllNetworkCalls();

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
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_pager_next").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect.verifySteps(["web_search_read"]);

    await contains(".o_pager_next").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect.verifySteps(["web_search_read"]);
});

test.tags("desktop");
test("pager, ungrouped, with count limit reached, click next (2) on desktop", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    Partner._records.push({ id: 5, foo: "xxx" });

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
    });

    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");

    await contains(".o_pager_next").click();

    expect(".o_pager_value").toHaveText("3-4");
    expect(".o_pager_limit").toHaveText("4+");

    await contains(".o_pager_next").click();

    expect(".o_pager_value").toHaveText("5-5");
    expect(".o_pager_limit").toHaveText("5");
});

test("pager, ungrouped, with count limit reached, click previous", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    Partner._records.push({ id: 5, foo: "xxx" });

    stepAllNetworkCalls();

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
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_pager_previous").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect.verifySteps(["search_count", "web_search_read"]);
});

test.tags("desktop");
test("pager, ungrouped, with count limit reached, click previous on desktop", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    Partner._records.push({ id: 5, foo: "xxx" });

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
    });

    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");

    await contains(".o_pager_previous").click();

    expect(".o_pager_value").toHaveText("5-5");
    expect(".o_pager_limit").toHaveText("5");
});

test.tags("desktop");
test("pager, ungrouped, with count limit reached, edit pager", async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    Partner._records.push({ id: 5, foo: "xxx" });
    stepAllNetworkCalls();

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
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains("span.o_pager_value").click();
    await contains("input.o_pager_value").edit("2-4");

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);
    expect(".o_pager_value").toHaveText("2-4");
    expect(".o_pager_limit").toHaveText("4+");
    expect.verifySteps(["web_search_read"]);

    await contains("span.o_pager_value").click();
    await contains("input.o_pager_value").edit("2-14");

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);
    expect(".o_pager_value").toHaveText("2-5");
    expect(".o_pager_limit").toHaveText("5");
    expect.verifySteps(["web_search_read"]);
});

test.tags("desktop");
test("count_limit attrs set in arch", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="2" count_limit="3">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_pager_limit").click();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("4");
    expect.verifySteps(["search_count"]);
});

test.tags("desktop");
test("pager, ungrouped, deleting all records from last page", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <a role="menuitem" type="delete" class="dropdown-item">Delete</a>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(4);

    // move to next page
    await pagerNext();

    expect(getPagerValue()).toEqual([4, 4]);

    // delete a record
    await contains(".o_kanban_record a").click();

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(3);
});

test.tags("desktop");
test("pager, update calls onUpdatedPager", async () => {
    class TestKanbanController extends KanbanController {
        setup() {
            super.setup();
            onWillRender(() => {
                expect.step("render");
            });
        }

        async onUpdatedPager() {
            expect.step("onUpdatedPager");
        }
    }

    viewRegistry.add("test_kanban_view", {
        ...kanbanView,
        Controller: TestKanbanController,
    });
    after(() => viewRegistry.remove("test_kanban_view"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban js_class="test_kanban_view">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        limit: 3,
    });

    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(4);
    expect.step("next page");
    await contains(".o_pager_next").click();
    expect(getPagerValue()).toEqual([4, 4]);
    expect.verifySteps(["render", "next page", "render", "onUpdatedPager"]);
});

test("click on a button type='delete' to delete a record in a column", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <a role="menuitem" type="delete" class="dropdown-item o_delete">Delete</a>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(queryAll(".o_kanban_load_more", { root: getKanbanColumn(0) })).toHaveCount(0);

    await click(queryFirst(".o_kanban_record .o_delete", { root: getKanbanColumn(0) }));
    await animationFrame();
    expect(".modal").toHaveCount(1);

    await contains(".modal .btn-primary").click();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".o_kanban_load_more", { root: getKanbanColumn(0) })).toHaveCount(0);
});

test("click on a button type='archive' to archive a record in a column", async () => {
    onRpc("action_archive", ({ args }) => {
        expect.step(`archive:${args[0]}`);
        return true;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <a role="menuitem" type="archive" class="dropdown-item o_archive">archive</a>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);

    await contains(".o_kanban_record .o_archive").click();

    expect(".modal").toHaveCount(1);
    expect.verifySteps([]);

    await contains(".modal .btn-primary").click();

    expect.verifySteps(["archive:1"]);
});

test("click on a button type='unarchive' to unarchive a record in a column", async () => {
    onRpc("action_unarchive", ({ args }) => {
        expect.step(`unarchive:${args[0]}`);
        return true;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="card">
                        <a role="menuitem" type="unarchive" class="dropdown-item o_unarchive">unarchive</a>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);

    await contains(".o_kanban_record .o_unarchive").click();

    expect.verifySteps(["unarchive:1"]);
});

test.tags("desktop");
test("kanban with an action id as on_create attrs", async () => {
    mockService("action", {
        doAction(action, options) {
            // simplified flow in this test: simulate a target new action which
            // creates a record and closes itself
            expect.step(`doAction ${action}`);
            Partner._records.push({ id: 299, foo: "new" });
            options.onClose();
        },
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="some.action">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);
    await createKanbanRecord();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "doAction some.action",
        "web_search_read",
    ]);
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
    expect(".o_column_quick_create").toHaveCount(1);

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

test("prevent deletion when grouped by many2many field", async () => {
    Partner._records[0].category_ids = [6, 7];
    Partner._records[3].category_ids = [7];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <t t-if="widget.deletable"><span class="thisisdeletable">delete</span></t>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_foo" domain="[]" string="GroupBy Foo" context="{ 'group_by': 'foo' }"/>
            </search>`,
        groupBy: ["category_ids"],
    });

    expect(".thisisdeletable").toHaveCount(0, { message: "records should not be deletable" });

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Foo");

    expect(".thisisdeletable").toHaveCount(4, { message: "records should be deletable" });
});

test.tags("desktop");
test("kanban grouped by many2one: false column is folded by default", async () => {
    Partner._records[0].product_id = false;

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
    });

    expect(".o_kanban_group").toHaveCount(3);
    expect(".o_column_folded").toHaveCount(1);
    expect(queryAllTexts(".o_kanban_header")).toEqual(["None\n(1)", "hello\n(1)", "xmo\n(2)"]);

    await contains(".o_kanban_header").click();

    expect(".o_column_folded").toHaveCount(0);
    expect(queryAllTexts(".o_kanban_header")).toEqual(["None\n(1)", "hello\n(1)", "xmo\n(2)"]);

    // reload -> None column should remain open
    await click(".o_searchview_input");
    await press("Enter");
    await animationFrame();

    expect(".o_column_folded").toHaveCount(0);
    expect(queryAllTexts(".o_kanban_header")).toEqual(["None\n(1)", "hello\n(1)", "xmo\n(2)"]);
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "get_views", // form view in quick create
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "web_read", // read the created record
        "onchange", // new quick create
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "get_views", // form view in quick create
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "web_search_read", // read records when unfolding 'None'
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "get_views", // get form view
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "web_read", // read the created record
        "onchange", // reopen the quick create automatically
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "get_views", // get form view
        "onchange", // quick create
        "web_save", // should perform a web_save to create the record
        "web_read",
        "onchange",
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
        "web_search_read",
        "web_search_read",
    ]);

    await createKanbanRecord();
    expect.verifySteps(["onchange"]);

    // do not fill anything and validate
    await validateKanbanRecord();

    expect.verifySteps([]);
    expect(".o_kanban_group:first-child .o_kanban_quick_create").toHaveCount(1);
    expect("[name=display_name]").toHaveClass("o_field_invalid");
    expect(".o_notification_manager .o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText("Invalid fields:\nDisplay Name");
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
    ]);

    // click on 'Create' -> should open the quick create in the first column
    await quickCreateKanbanRecord();
    expect.verifySteps(["get_views", "onchange"]);

    // fill the 'foo' field -> should trigger the onchange
    await editKanbanRecordQuickCreateInput("foo", "new partner");
    expect.verifySteps(["onchange"]);

    await validateKanbanRecord();
    expect.verifySteps(["web_save", "web_read", "onchange"]);
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
    await contains(".o_kanban_group:first-child .o_kanban_record:last-of-type").click();
    expect(".o_kanban_quick_create").toHaveCount(0);

    // click to input and drag the mouse outside, should not cancel the quick creation
    await quickCreateKanbanRecord();
    await (
        await drag(".o_kanban_quick_create input")
    ).drop(".o_kanban_group:first-child .o_kanban_record:last-of-type");
    await animationFrame();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been destroyed after clicking outside",
    });

    // click to really add an element
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("foo", "new partner");

    // clicking outside should no longer destroy the quick create as it is dirty
    await contains(".o_kanban_group:first-child .o_kanban_record:last-of-type").click();
    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been destroyed",
    });

    // confirm by pressing ENTER
    await press("Enter");
    await animationFrame();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);
    expect(getKanbanRecordTexts(0)).toEqual(["new partner", "blip"]);
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

    // click outside: should not remove the quick create
    await contains(".o_kanban_group:first-child .o_kanban_record").click();

    expect(".o_kanban_quick_create").toHaveCount(1, {
        message: "the quick create should not have been destroyed",
    });

    // press ESC: should remove the quick create
    await press("Escape");
    await animationFrame();

    expect(".o_kanban_quick_create").toHaveCount(0, {
        message: "quick create widget should have been removed",
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
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should still contain one record",
    });
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

test("quick create is disabled until record is created and read", async () => {
    const def = new Deferred();
    onRpc("web_read", () => def);

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
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should still contain one record",
    });
    expect(".o_kanban_quick_create.o_disabled").toHaveCount(1, {
        message: "quick create should be disabled",
    });

    def.resolve();
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
    Partner._views["form,false"] = `
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
    Partner._views["kanban,false"] = `
        <kanban sample="1">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;
    Partner._views["search,false"] = "<search/>";
    Partner._views["list,false"] = '<list><field name="foo"/></list>';
    Partner._views["form,false"] = `
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
    Partner._views["form,false"] = `
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

    Partner._views["form,false"] = '<form><field name="foo"/></form>';

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

    Partner._views["form,false"] = '<form><field name="state"/></form>';

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
    expect(".modal .o_field_widget[name=state] select:first").toHaveValue('"abc"');

    await contains(".modal .o_form_button_save").click();

    expect(".modal .o_form_view .o_form_editable").toHaveCount(0);
    expect(".o_kanban_group:first .o_kanban_record").toHaveCount(2);
});

test.tags("desktop");
test("quick create record in empty grouped kanban", async () => {
    onRpc("web_read_group", () => {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "xplone"],
                },
                {
                    __domain: [["product_id", "=", 5]],
                    product_id_count: 0,
                    product_id: [5, "xplan"],
                },
            ],
            length: 2,
        };
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
    expect(".o_kanban_quick_create select:first").toHaveValue('"abc"', {
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
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);

    // add a new column
    expect(".o_column_quick_create .o_quick_create_folded").toHaveCount(1);

    await quickCreateKanbanColumn();

    expect(".o_column_quick_create .o_quick_create_unfolded").toHaveCount(1);

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

test("many2many_tags in kanban views", async () => {
    Partner._records[0].category_ids = [6, 7];
    Partner._records[1].category_ids = [7, 8];
    Category._records.push({
        id: 8,
        name: "hello",
        color: 0,
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="category_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                        <field name="foo"/>
                        <field name="state" widget="priority"/>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect(resId).toBe(1, {
                message: "should trigger an event to open the clicked record in a form view",
            });
        },
    });

    expect(
        queryAll(".o_field_many2many_tags .o_tag", { root: getKanbanRecord({ index: 0 }) })
    ).toHaveCount(2, {
        message: "first record should contain 2 tags",
    });
    expect(queryAll(".o_tag.o_tag_color_2", { root: getKanbanRecord({ index: 0 }) })).toHaveCount(
        1,
        {
            message: "first tag should have color 2",
        }
    );
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    // Checks that second records has only one tag as one should be hidden (color 0)
    expect(".o_kanban_record:nth-child(2) .o_tag").toHaveCount(1, {
        message: "there should be only one tag in second record",
    });
    expect(".o_kanban_record:nth-child(2) .o_tag:first").toHaveText("silver");

    // Write on the record using the priority widget to trigger a re-render in readonly
    await contains(".o_kanban_record:first-child .o_priority_star:first-child").click();

    expect.verifySteps(["web_save"]);
    expect(".o_kanban_record:first-child .o_field_many2many_tags .o_tag").toHaveCount(2, {
        message: "first record should still contain only 2 tags",
    });
    const tags = queryAll(".o_kanban_record:first-child .o_tag");
    expect(tags[0]).toHaveText("gold");
    expect(tags[1]).toHaveText("silver");

    // click on a tag (should trigger switch_view)
    await contains(".o_kanban_record:first-child .o_tag:first-child").click();
});

test("priority field should not be editable when missing access rights", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban edit="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="state" widget="priority"/>
                    </t>
                </templates>
            </kanban>`,
    });
    // Try to fill one star in the priority field of the first record
    await contains(".o_kanban_record:first-child .o_priority_star:first-child").click();
    expect(".o_kanban_record:first-child .o_priority .fa-star-o").toHaveCount(2, {
        message: "first record should still contain 2 empty stars",
    });
});

test("Do not open record when clicking on `a` with `href`", async () => {
    expect.assertions(6);

    Partner._records = [{ id: 1, foo: "yop" }];

    mockService("action", {
        async switchView() {
            // when clicking on a record in kanban view,
            // it switches to form view.
            expect.step("switchView");
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <a class="o_test_link" href="#">test link</a>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record a").toHaveCount(1);

    expect(".o_kanban_record a").toHaveAttribute("href", null, {
        message: "link inside kanban record should have non-empty href",
    });

    // Prevent the browser default behaviour when clicking on anything.
    // This includes clicking on a `<a>` with `href`, so that it does not
    // change the URL in the address bar.
    // Note that we should not specify a click listener on 'a', otherwise
    // it may influence the kanban record global click handler to not open
    // the record.
    const testLink = queryFirst(".o_kanban_record a");
    testLink.addEventListener("click", (ev) => {
        expect(ev.defaultPrevented).toBe(false, {
            message: "should not prevented browser default behaviour beforehand",
        });
        expect(ev.target).toBe(testLink, {
            message: "should have clicked on the test link in the kanban record",
        });
        ev.preventDefault();
    });

    await click(".o_kanban_record a");

    expect.verifySteps([]);
});

test("Open record when clicking on widget field", async function (assert) {
    expect.assertions(2);

    Product._views["form,false"] = `<form string="Product"><field name="display_name"/></form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="salary" widget="monetary"/>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect(resId).toBe(1, { message: "should trigger an event to open the form view" });
        },
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    await click(".o_field_monetary[name=salary]");
});

test("o2m loaded in only one batch", async () => {
    class Subtask extends models.Model {
        _name = "subtask";

        name = fields.Char();

        _records = [
            { id: 1, name: "subtask #1" },
            { id: 2, name: "subtask #2" },
        ];
    }
    defineModels([Subtask]);
    Partner._fields.subtask_ids = fields.One2many({ relation: "subtask" });
    Partner._records[0].subtask_ids = [1];
    Partner._records[1].subtask_ids = [2];

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="subtask_ids" widget="many2many_tags"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    await validateSearch();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("kanban with many2many, load and reload", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="category_ids" widget="many2many_tags"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    await press("Enter"); // reload
    await animationFrame();

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("kanban with reference field", async () => {
    Partner._fields.ref_product = fields.Reference({ selection: [["product", "Product"]] });
    Partner._records[0].ref_product = "product,3";
    Partner._records[1].ref_product = "product,5";

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        groupBy: ["product_id"],
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="ref_product"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await press("Enter"); // reload
    await animationFrame();

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
    expect(queryAllTexts(".o_kanban_record span")).toEqual(["hello", "", "xmo", ""]);
});

test.tags("desktop");
test("drag and drop a record with load more", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="1">
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(queryAllTexts(".o_kanban_group:eq(0) .o_kanban_record")).toEqual(["4"]);
    expect(queryAllTexts(".o_kanban_group:eq(1) .o_kanban_record")).toEqual(["1"]);

    await contains(".o_kanban_group:eq(1) .o_kanban_record").dragAndDrop(".o_kanban_group:eq(0)");
    expect(queryAllTexts(".o_kanban_group:eq(0) .o_kanban_record")).toEqual(["4", "1"]);
    expect(queryAllTexts(".o_kanban_group:eq(1) .o_kanban_record")).toEqual(["2"]);
});

test.tags("desktop");
test("can drag and drop a record from one column to the next", async () => {
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <t t-if="widget.editable">
                            <span class="thisiseditable">edit</span>
                        </t>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(".thisiseditable").toHaveCount(4);

    expect.verifySteps([]);

    // first record of first column moved to the bottom of second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect(".thisiseditable").toHaveCount(4);

    expect.verifySteps(["resequence"]);
});

test.tags("desktop");
test("user without permission cannot drag and drop a column thus sequence remains unchanged on drag and drop attempt", async () => {
    expect.errors(1);

    onRpc("/web/dataset/resequence", () => {
        throw makeServerError({ message: "No Permission" }); // Simulate user without permission
    });

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
    });

    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(2)", "xmo\n(2)"]);

    const groups = queryAll(".o_column_title");
    await contains(groups[0]).dragAndDrop(groups[1]);

    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(2)", "xmo\n(2)"]);

    expect.verifyErrors(["No Permission"]);
});

test.tags("desktop");
test("user without permission cannot drag and drop a record thus sequence remains unchanged on drag and drop attempt", async () => {
    expect.errors(1);

    onRpc("partner", "web_save", () => {
        throw makeServerError({ message: "No Permission" }); // Simulate user without permission
    });

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
    });

    expect(".o_kanban_record:first").toHaveText("yop", {
        message: "Checking the initial state of the view",
    });

    await contains(".o_kanban_record").dragAndDrop(".o_kanban_group:nth-child(2)");

    expect(".o_kanban_record:first").toHaveText("yop", {
        message: "Do not let the user d&d the record without permission",
    });

    await contains(".o_kanban_record").dragAndDrop(".o_kanban_record:nth-child(3)");

    expect(".o_kanban_record:first").toHaveText("gnap", {
        message: "Check that the record does not become static after d&d",
    });

    expect.verifyErrors(["No Permission"]);
});

test.tags("desktop");
test("drag and drop highlight on hover", async () => {
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
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    // first record of first column moved to the bottom of second column
    const { drop, moveTo } = await contains(".o_kanban_group:first-child .o_kanban_record").drag();
    await moveTo(".o_kanban_group:nth-child(2)");

    expect(getKanbanColumn(1)).toHaveClass("o_kanban_hover");

    await drop();

    expect(".o_kanban_group:nth-child(2).o_kanban_hover").toHaveCount(0);
});

test("drag and drop outside of a column", async () => {
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
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    // first record of first column moved to the right of a column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_column_quick_create"
    );
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
});

test.tags("desktop");
test("drag and drop a record, grouped by selection", async () => {
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return true;
    });
    onRpc("partner", "web_save", ({ args }) => {
        expect.step(args[1]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="state"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["state"],
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect.verifySteps([]);

    // first record of second column moved to the bottom of first column
    await contains(".o_kanban_group:nth-child(2) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first-child"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(0);
    expect.verifySteps([{ state: "abc" }, "resequence"]);
});

test.tags("desktop");
test("prevent drag and drop of record if grouped by readonly", async () => {
    // Whether the kanban is grouped by state, foo, bar or product_id
    // the user must not be able to drag and drop from one group to another,
    // as state, foo bar, product_id are made readonly one way or another.
    // state must not be draggable:
    // state is not readonly in the model. state is passed in the arch specifying readonly="1".
    // foo must not be draggable:
    // foo is readonly in the model fields. foo is passed in the arch but without specifying readonly.
    // bar must not be draggable:
    // bar is readonly in the model fields. bar is not passed in the arch.
    // product_id must not be draggable:
    // product_id is readonly in the model fields. product_id is passed in the arch specifying readonly="0",
    // but the readonly in the model takes over.
    Partner._fields.foo = fields.Char({ readonly: true });
    Partner._fields.bar = fields.Boolean({ readonly: true });
    Partner._fields.product_id = fields.Many2one({ relation: "product", readonly: true });

    onRpc("/web/dataset/resequence", () => true);
    onRpc("partner", "write", () => {
        expect.step("should not be called");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="foo"/>
                            <field name="product_id" readonly="0" invisible="1"/>
                            <field name="state" readonly="1"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_foo" domain="[]" string="GroupBy Foo" context="{ 'group_by': 'foo' }"/>
                <filter name="group_by_bar" domain="[]" string="GroupBy Bar" context="{ 'group_by': 'bar' }"/>
                <filter name="group_by_product" domain="[]" string="GroupBy Product" context="{ 'group_by': 'product_id' }"/>
            </search>`,
        groupBy: ["state"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);

    // first record of first column moved to the bottom of second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not be draggable
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Foo");

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(1);

    // first record of first column moved to the bottom of second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not be draggable
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(1);

    expect(getKanbanRecordTexts(0)).toEqual(["blipDEF", "blipGHI"]);

    // second record of first column moved at first place
    await contains(".o_kanban_group:first-child .o_kanban_record:last-of-type").dragAndDrop(
        ".o_kanban_group:first-child .o_kanban_record"
    );

    // should still be able to resequence
    expect(getKanbanRecordTexts(0)).toEqual(["blipGHI", "blipDEF"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Foo");
    await toggleMenuItem("GroupBy Bar");

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(0);

    expect(getKanbanRecordTexts(0)).toEqual(["blipGHI"]);

    // first record of first column moved to the bottom of second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not be draggable
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(0);

    expect(getKanbanRecordTexts(0)).toEqual(["blipGHI"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Bar");
    await toggleMenuItem("GroupBy Product");

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(0);

    expect(getKanbanRecordTexts(0)).toEqual(["yopABC", "gnapGHI"]);

    // first record of first column moved to the bottom of second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not be draggable
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(0);

    expect(getKanbanRecordTexts(0)).toEqual(["yopABC", "gnapGHI"]);
    expect.verifySteps([]);
});

test("prevent drag and drop if grouped by date/datetime field", async () => {
    Partner._records[0].date = "2017-01-08";
    Partner._records[1].date = "2017-01-09";
    Partner._records[2].date = "2017-02-08";
    Partner._records[3].date = "2017-02-10";
    Partner._records[0].datetime = "2017-01-08 10:55:05";
    Partner._records[1].datetime = "2017-01-09 11:31:10";
    Partner._records[2].datetime = "2017-02-08 09:20:25";
    Partner._records[3].datetime = "2017-02-10 08:05:51";

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
        searchViewArch: `
            <search>
                <filter name="group_by_datetime" domain="[]" string="GroupBy Datetime" context="{ 'group_by': 'datetime' }"/>
            </search>`,
        groupBy: ["date:month"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "1st column should contain 2 records of January month",
    });
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "2nd column should contain 2 records of February month",
    });

    // drag&drop a record in another column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not drag&drop record
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "Should remain same records in first column (2 records)",
    });
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "Should remain same records in 2nd column (2 record)",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Datetime");
    await toggleMenuItemOption("GroupBy Datetime", "Month");

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "1st column should contain 2 records of January month",
    });
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "2nd column should contain 2 records of February month",
    });

    // drag&drop a record in another column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not drag&drop record
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "Should remain same records in first column(2 records)",
    });
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "Should remain same records in 2nd column(2 record)",
    });
});

test.tags("desktop");
test("prevent drag and drop if grouped by many2many field", async () => {
    Partner._records[0].category_ids = [6, 7];
    Partner._records[3].category_ids = [7];

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
        searchViewArch: `
            <search>
                <filter name="group_by_state" domain="[]" string="GroupBy State" context="{ 'group_by': 'state' }"/>
            </search>`,
        groupBy: ["category_ids"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_column_title:first").toHaveText("gold\n(2)", {
        message: "first column should have correct title",
    });
    expect(".o_kanban_group:last-child .o_column_title:first").toHaveText("silver\n(3)", {
        message: "second column should have correct title",
    });
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3);

    // drag&drop a record in another column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3);

    // Sanity check: groupby a non m2m field and check dragdrop is working
    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy State");

    expect(".o_kanban_group").toHaveCount(3);
    expect(queryAllTexts(".o_kanban_group .o_column_title")).toEqual([
        "ABC\n(1)",
        "DEF\n(1)",
        "GHI\n(2)",
    ]);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1, {
        message: "first column should have 1 record",
    });
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(2, {
        message: "last column should have 2 records",
    });

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:last-child"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(0, {
        message: "first column should not contain records",
    });
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3, {
        message: "last column should contain 3 records",
    });
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

test("completely prevent drag and drop if records_draggable set to false", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban records_draggable="false">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // testing initial state
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(getKanbanRecordTexts()).toEqual(["yop", "gnap", "blip", "blip"]);
    expect(".o_draggable").toHaveCount(0);

    // attempt to drag&drop a record in another column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not drag&drop record
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2, {
        message: "First column should still contain 2 records",
    });
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2, {
        message: "Second column should still contain 2 records",
    });
    expect(getKanbanRecordTexts()).toEqual(["yop", "gnap", "blip", "blip"], {
        message: "Records should not have moved",
    });

    // attempt to drag&drop a record in the same column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first-child .o_kanban_record:last-of-type"
    );

    expect(getKanbanRecordTexts()).toEqual(["yop", "gnap", "blip", "blip"], {
        message: "Records should not have moved",
    });
});

test.tags("desktop");
test("prevent drag and drop of record if save fails", async () => {
    expect.errors(1);

    onRpc("partner", "web_save", () => {
        throw new Error("Save failed");
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="product_id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    // drag&drop a record in another column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    // should not be dropped, card should reset back to first column
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    expect.verifyErrors(["Save failed"]);
});

test("kanban view with default_group_by", async () => {
    expect.assertions(13);

    Partner._records[0].product_id = 1;
    Product._records.push({ id: 1, display_name: "third product" });

    let readGroupCount = 0;
    onRpc("web_read_group", ({ kwargs }) => {
        readGroupCount++;
        switch (readGroupCount) {
            case 1:
                return expect(kwargs.groupby).toEqual(["bar"]);
            case 2:
                return expect(kwargs.groupby).toEqual(["product_id"]);
            case 3:
                return expect(kwargs.groupby).toEqual(["bar"]);
        }
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_product_id" domain="[]" string="GroupBy Product" context="{ 'group_by': 'product_id' }"/>
            </search>`,
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group").toHaveCount(2);
    // open search bar in mobile
    if (queryAll(".o_control_panel_navigation > button").length) {
        await contains(".o_control_panel_navigation > button").click();
    }
    expect(`.o_searchview_facet`).toHaveCount(1);
    expect(`.o_searchview_facet`).toHaveText("Bar");

    // simulate an update coming from the searchview, with another groupby given
    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Product");
    expect(".o_kanban_group").toHaveCount(3);
    expect(`.o_searchview_facet`).toHaveCount(1);
    expect(`.o_searchview_facet`).toHaveText("GroupBy Product");

    // simulate an update coming from the searchview, removing the previously set groupby
    await contains(".o_searchview_facet .o_facet_remove").click();
    expect(".o_kanban_group").toHaveCount(2);
    expect(`.o_searchview_facet`).toHaveCount(1);
    expect(`.o_searchview_facet`).toHaveText("Bar");
});

test.tags("desktop");
test("kanban view not groupable", async () => {
    patchWithCleanup(kanbanView, { searchMenuTypes: ["filter", "favorite"] });

    onRpc("web_read_group", () => {
        expect.step("web_read_group");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter string="Filter" name="filter" domain="[]"/>
                <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
            </search>`,
        context: { search_default_itsName: 1 },
    });

    expect(".o_kanban_renderer").not.toHaveClass("o_kanban_grouped");
    expect(".o_control_panel div.o_search_options div.o_group_by_menu").toHaveCount(0);
    expect(getFacetTexts()).toEqual([]);

    // validate presence of the search arch info
    await toggleSearchBarMenu();
    expect(".o_filter_menu .o_menu_item").toHaveCount(2);
    expect.verifySteps([]);
});

test("kanban view with create=False", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban create="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o-kanban-button-new").toHaveCount(0);
});

test("kanban view with create=False and groupby", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban create="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o-kanban-button-new").toHaveCount(0);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_quick_add").toHaveCount(0);
});

test("clicking on a link triggers correct event", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <a type="open">Edit</a>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId, { mode }) => {
            expect(resId).toBe(1);
            expect(mode).toBe("edit");
        },
    });
    await contains("a", { root: getKanbanRecord({ index: 0 }) }).click();
});

test.tags("desktop");
test("environment is updated when (un)folding groups", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    // fold the second group and check that the res_ids it contains are no
    // longer in the environment
    const clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Fold");

    expect(getKanbanRecordTexts()).toEqual(["1", "3"]);

    // re-open the second group and check that the res_ids it contains are
    // back in the environment
    await contains(getKanbanColumn(1)).click();

    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);
});

test.tags("desktop");
test("create a column in grouped on m2o", async () => {
    onRpc("/web/dataset/resequence", async (request) => {
        expect.step("/web/dataset/resequence");
        const { params } = await request.json();
        expect.step(params.ids.toString());
    });
    onRpc("name_create", () => {
        expect.step("name_create");
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

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a quick create column",
    });
    expect(".o_column_quick_create input").toHaveCount(0, {
        message: "the input should not be visible",
    });

    await quickCreateKanbanColumn();

    expect(".o_column_quick_create input").toHaveCount(1, {
        message: "the input should be visible",
    });

    // discard the column creation and click it again
    await press("Escape");
    await animationFrame();

    expect(".o_column_quick_create input").toHaveCount(0, {
        message: "the input should not be visible",
    });

    await quickCreateKanbanColumn();

    expect(".o_column_quick_create input").toHaveCount(1, {
        message: "the input should be visible",
    });

    await editKanbanColumnName("new value");
    await validateKanbanColumn();

    expect(".o_kanban_group").toHaveCount(3);
    expect(
        queryAll(".o_column_title:contains(new value)", { root: getKanbanColumn(2) })
    ).toHaveCount(1, {
        message: "the last column should be the newly created one",
    });
    expect(!!getKanbanColumn(2).dataset.id).toBe(true, {
        message: "the created column should have an associated id",
    });
    expect(getKanbanColumn(2)).not.toHaveClass("o_column_folded", {
        message: "the created column should not be folded",
    });
    expect.verifySteps(["name_create", "/web/dataset/resequence", "3,5,6"]);

    // fold and unfold the created column, and check that no RPCs are done (as there are no records)
    const clickColumnAction = await toggleKanbanColumnActions(2);
    await clickColumnAction("Fold");

    expect(getKanbanColumn(2)).toHaveClass("o_column_folded");

    await click(getKanbanColumn(2));
    await animationFrame();

    expect(getKanbanColumn(1)).not.toHaveClass("o_column_folded");
    // no rpc should have been done when folding/unfolding
    expect.verifySteps([]);

    // quick create a record
    await createKanbanRecord();

    expect(queryOne(".o_kanban_quick_create", { root: getKanbanColumn(0) })).toHaveCount(1);
});

test("create a column in grouped on m2o without sequence field on view model", async () => {
    delete Partner._fields.sequence;

    onRpc("name_create", () => {
        expect.step("name_create");
    });
    onRpc("/web/dataset/resequence", async (request) => {
        expect.step("resequence");
        const { params } = await request.json();
        expect.step(params.ids.toString());
        return true;
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

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a quick create column",
    });
    expect(".o_column_quick_create input").toHaveCount(0, {
        message: "the input should not be visible",
    });

    await quickCreateKanbanColumn();
    await editKanbanColumnName("new value");
    await validateKanbanColumn();

    expect.verifySteps(["name_create", "resequence", "3,5,6"]);
});

test.tags("desktop");
test("auto fold group when reach the limit", async () => {
    for (let i = 0; i < 12; i++) {
        Product._records.push({ id: 8 + i, name: `column ${i}` });
        Partner._records.push({ id: 20 + i, foo: "dumb entry", product_id: 8 + i });
    }
    Product._records[2].fold = true;
    Product._records[8].fold = true;

    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read domain: ${kwargs.domain}`);
    });

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
    });

    // we look if column are folded/unfolded according to what is expected
    expect(getKanbanColumn(1)).not.toHaveClass("o_column_folded");
    expect(getKanbanColumn(3)).not.toHaveClass("o_column_folded");
    expect(getKanbanColumn(9)).not.toHaveClass("o_column_folded");
    expect(getKanbanColumn(2)).toHaveClass("o_column_folded");
    expect(getKanbanColumn(8)).toHaveClass("o_column_folded");

    // we look if columns are actually folded after we reached the limit
    expect(getKanbanColumn(12)).toHaveClass("o_column_folded");
    expect(getKanbanColumn(13)).toHaveClass("o_column_folded");

    // we look if we have the right count of folded/unfolded column
    expect(".o_kanban_group:not(.o_column_folded)").toHaveCount(10);
    expect(".o_kanban_group.o_column_folded").toHaveCount(4);

    expect.verifySteps([
        "web_search_read domain: product_id,=,3",
        "web_search_read domain: product_id,=,5",
        "web_search_read domain: product_id,=,9",
        "web_search_read domain: product_id,=,10",
        "web_search_read domain: product_id,=,11",
        "web_search_read domain: product_id,=,12",
        "web_search_read domain: product_id,=,13",
        "web_search_read domain: product_id,=,15",
        "web_search_read domain: product_id,=,16",
        "web_search_read domain: product_id,=,17",
    ]);
});

test.tags("desktop", "focus required");
test("show/hide help message (ESC) in quick create", async () => {
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
    });

    await quickCreateKanbanColumn();
    await animationFrame(); // Wait for the autofocus to trigger after the update

    expect(".o_discard_msg").toHaveCount(1, { message: "the ESC to discard message is visible" });

    // click outside the column (to lose focus)
    await click(".o_kanban_header");
    await animationFrame();

    expect(".o_discard_msg").toHaveCount(0, {
        message: "the ESC to discard message is no longer visible",
    });
});

test.tags("desktop");
test("delete a column in grouped on m2o", async () => {
    stepAllNetworkCalls();
    let resequencedIDs = [];
    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        resequencedIDs = params.ids;
        expect(resequencedIDs.filter(isNaN).length).toBe(0, {
            message: "column resequenced should be existing records with IDs",
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test" on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // check the initial rendering
    expect(".o_kanban_group").toHaveCount(2, { message: "should have two columns" });
    expect(queryText(".o_column_title", { root: getKanbanColumn(0) })).toBe("hello\n(2)");
    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("xmo\n(2)");
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2, {
        message: "second column should have two records",
    });

    // check available actions in kanban header's config dropdown
    await toggleKanbanColumnActions(0);
    expect(queryAll(".o_kanban_toggle_fold", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(
        1,
        {
            message: "should be able to fold the column",
        }
    );
    expect(queryAll(".o_column_edit", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(1, {
        message: "should be able to edit the column",
    });
    expect(queryAll(".o_column_delete", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(1, {
        message: "should be able to delete the column",
    });
    expect(
        queryAll(".o_column_archive_records", { root: getKanbanColumnDropdownMenu(0) })
    ).toHaveCount(0, { message: "should not be able to archive all the records" });
    expect(queryAll(".o_column_unarchive_records", { root: getKanbanColumn(0) })).toHaveCount(0, {
        message: "should not be able to restore all the records",
    });

    // delete second column (first cancel the confirm request, then confirm)
    let clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Delete");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-secondary").click();

    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("xmo\n(2)");

    clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Delete");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("hello\n(2)");
    expect(".o_kanban_group").toHaveCount(2, { message: "should still have two columns" });
    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("None\n(2)", {
        message: "first column should have no id (Undefined column)",
    });

    // check available actions on 'Undefined' column
    await click(getKanbanColumn(0));
    await animationFrame();
    await toggleKanbanColumnActions(0);

    expect(queryAll(".o_kanban_toggle_fold", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(
        1,
        {
            message: "should be able to fold the column",
        }
    );
    expect(queryAll(".o_column_edit", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(0, {
        message: "should be able to edit the column",
    });
    expect(queryAll(".o_column_delete", { root: getKanbanColumnDropdownMenu(0) })).toHaveCount(0, {
        message: "should not be able to delete the column",
    });
    expect(
        queryAll(".o_column_archive_records", { root: getKanbanColumnDropdownMenu(0) })
    ).toHaveCount(0, { message: "should not be able to archive all the records" });
    expect(
        queryAll(".o_column_unarchive_records", { root: getKanbanColumnDropdownMenu(0) })
    ).toHaveCount(0, { message: "should not be able to restore all the records" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "unlink",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
    expect(".o_kanban_group").toHaveCount(2, {
        message: "the old groups should have been correctly deleted",
    });

    // test column drag and drop having an 'Undefined' column
    expect(getKanbanColumn(0)).not.toHaveClass("o_group_draggable");
    await contains(".o_kanban_group:first-child .o_column_title").dragAndDrop(
        queryAll(".o_kanban_group")[1]
    );

    expect(resequencedIDs).toEqual([], {
        message: "resequencing require at least 2 not Undefined columns",
    });

    await quickCreateKanbanColumn();
    await editKanbanColumnName("once third column");
    await validateKanbanColumn();

    expect.verifySteps(["name_create", "/web/dataset/resequence"]);
    expect(resequencedIDs).toEqual([3, 4], {
        message: "creating a column should trigger a resequence",
    });

    await contains(".o_kanban_group:first-child .o_column_title").dragAndDrop(
        queryAll(".o_kanban_group")[2]
    );

    expect(resequencedIDs).toEqual([3, 4], {
        message: "moving the Undefined column should not affect order of other columns",
    });

    expect(getKanbanColumn(1)).toHaveClass("o_group_draggable");
    await contains(".o_kanban_group:nth-child(2) .o_column_title").dragAndDrop(
        queryAll(".o_kanban_group")[2]
    );
    expect.verifySteps(["/web/dataset/resequence"]);
    expect(resequencedIDs).toEqual([4, 3], {
        message: "moved column should be resequenced accordingly",
    });
});

test("create a column, delete it and create another one", async () => {
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

    expect(".o_kanban_group").toHaveCount(2);

    await quickCreateKanbanColumn();
    await editKanbanColumnName("new column 1");
    await validateKanbanColumn();

    expect(".o_kanban_group").toHaveCount(3);

    const clickColumnAction = await toggleKanbanColumnActions(2);
    await clickColumnAction("Delete");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_kanban_group").toHaveCount(2);

    await quickCreateKanbanColumn();
    await editKanbanColumnName("new column 2");
    await validateKanbanColumn();

    expect(".o_kanban_group").toHaveCount(3);
    expect(getKanbanColumn(2).querySelector("div")).toHaveText("new column 2\n(0)", {
        message: "the last column should be the newly created one",
    });
});

test("delete an empty column, then a column with records.", async () => {
    let firstLoad = true;

    onRpc("web_read_group", function ({ parent }) {
        // override read_group to return an extra empty groups
        const result = parent();
        if (firstLoad) {
            result.groups.unshift({
                __domain: [["product_id", "=", 7]],
                product_id: [7, "empty group"],
                product_id_count: 0,
            });
            result.length = 3;
            firstLoad = false;
        }
        return result;
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

    expect(".o_kanban_header .o_column_title:contains('empty group')").toHaveCount(1);
    expect(".o_kanban_header .o_column_title:contains('hello')").toHaveCount(1);
    expect(".o_kanban_header .o_column_title:contains('None')").toHaveCount(0);

    // Delete the empty group
    let clickColumnAction = await toggleKanbanColumnActions();
    await clickColumnAction("Delete");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    // Delete the group 'hello'
    clickColumnAction = await toggleKanbanColumnActions();
    await clickColumnAction("Delete");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    // None of the previous groups should be present inside the view. Instead, a 'none' column should be displayed.
    expect(".o_kanban_header span:contains('empty group')").toHaveCount(0);
    expect(".o_kanban_header span:contains('hello')").toHaveCount(0);
    expect(".o_kanban_header .o_column_title:contains('None')").toHaveCount(1);
});

test.tags("desktop");
test("edit a column in grouped on m2o", async () => {
    Product._views["form,false"] = `
        <form string="Product">
            <field name="name"/>
        </form>`;

    onRpc(() => {
        nbRPCs++;
    });

    let nbRPCs = 0;
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

    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("xmo\n(2)");

    // edit the title of column [5, 'xmo'] and close without saving
    let clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Edit");

    expect(".modal .o_form_editable").toHaveCount(1);
    expect(".modal .o_form_editable input").toHaveValue("xmo");

    await contains(".modal .o_form_editable input").edit("ged");
    nbRPCs = 0;
    await contains(".modal-header .btn-close").click();

    expect(".modal").toHaveCount(0);
    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("xmo\n(2)");
    expect(nbRPCs).toBe(0, { message: "no RPC should have been done" });

    // edit the title of column [5, 'xmo'] and discard
    clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Edit");
    await contains(".modal .o_form_editable input").edit("ged");
    nbRPCs = 0;
    await contains(".modal button.o_form_button_cancel").click();

    expect(".modal").toHaveCount(0);
    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("xmo\n(2)");
    expect(nbRPCs).toBe(0, { message: "no RPC should have been done" });

    // edit the title of column [5, 'xmo'] and save
    clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Edit");
    await contains(".modal .o_form_editable input").edit("ged");
    nbRPCs = 0;
    await click(".modal .o_form_button_save"); // click on save
    await animationFrame();

    expect(".modal").toHaveCount(0, { message: "the modal should be closed" });
    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("ged\n(2)");
    expect(nbRPCs).toBe(4, { message: "should have done 1 write, 1 read_group and 2 search_read" });
});

test("edit a column propagates right context", async () => {
    expect.assertions(4);

    Product._views["form,false"] = `
        <form string="Product">
            <field name="display_name"/>
        </form>`;

    serverState.lang = "nb_NO";

    onRpc(({ method, model, kwargs }) => {
        if (model === "partner" && method === "web_search_read") {
            expect(kwargs.context.lang).toBe("nb_NO", {
                message: "lang is present in context for partner operations",
            });
        } else if (model === "product") {
            expect(kwargs.context.lang).toBe("nb_NO", {
                message: "lang is present in context for product operations",
            });
        }
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

    const clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Edit");
});

test("quick create column should be opened if there is no column", async () => {
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
        domain: [["foo", "=", "norecord"]],
    });

    expect(".o_kanban_group").toHaveCount(0);
    expect(".o_column_quick_create").toHaveCount(1);
    expect(".o_column_quick_create input").toHaveCount(1, {
        message: "the quick create should be opened",
    });
});

test("quick create column should close on window click if there is no column", async () => {
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
        domain: [["foo", "=", "norecord"]],
    });

    expect(".o_kanban_group").toHaveCount(0);
    expect(".o_column_quick_create").toHaveCount(1);
    expect(".o_column_quick_create input").toHaveCount(1, {
        message: "the quick create should be opened",
    });
    // click outside should not discard quick create column
    await contains(".o_kanban_example_background_container").click();
    expect(".o_column_quick_create input").toHaveCount(0, {
        message: "the quick create should be closed",
    });
});

test("quick create several columns in a row", async () => {
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
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "should have two columns" });
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a ColumnQuickCreate widget",
    });
    expect(".o_column_quick_create .o_quick_create_folded:visible").toHaveCount(1, {
        message: "the ColumnQuickCreate should be folded",
    });
    expect(".o_column_quick_create .o_quick_create_unfolded:visible").toHaveCount(0, {
        message: "the ColumnQuickCreate should be folded",
    });

    // add a new column
    await quickCreateKanbanColumn();
    expect(".o_column_quick_create .o_quick_create_folded:visible").toHaveCount(0, {
        message: "the ColumnQuickCreate should be unfolded",
    });
    expect(".o_column_quick_create .o_quick_create_unfolded:visible").toHaveCount(1, {
        message: "the ColumnQuickCreate should be unfolded",
    });
    await editKanbanColumnName("New Column 1");
    await validateKanbanColumn();
    expect(".o_kanban_group").toHaveCount(3, { message: "should now have three columns" });

    // add another column
    expect(".o_column_quick_create .o_quick_create_folded:visible").toHaveCount(0, {
        message: "the ColumnQuickCreate should still be unfolded",
    });
    expect(".o_column_quick_create .o_quick_create_unfolded:visible").toHaveCount(1, {
        message: "the ColumnQuickCreate should still be unfolded",
    });
    await editKanbanColumnName("New Column 2");
    await validateKanbanColumn();
    expect(".o_kanban_group").toHaveCount(4);
});

test.tags("desktop");
test("quick create column with enter", async () => {
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
    });

    await quickCreateKanbanColumn();
    await edit("New Column 1");
    await animationFrame();
    expect(".o_kanban_group").toHaveCount(2);

    await press("Enter");
    await animationFrame();
    expect(".o_kanban_group").toHaveCount(3);
});

test.tags("desktop");
test("quick create column and examples", async () => {
    registry.category("kanban_examples").add("test", {
        allowedGroupBys: ["product_id"],
        examples: [
            {
                name: "A first example",
                columns: ["Column 1", "Column 2", "Column 3"],
                description: "A weak description.",
            },
            {
                name: "A second example",
                columns: ["Col 1", "Col 2"],
                description: `A fantastic description.`,
            },
        ],
    });
    after(() => registry.category("kanban_examples").remove("test"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban examples="test">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have quick create available",
    });

    // open the quick create
    await quickCreateKanbanColumn();

    expect(".o_column_quick_create .o_kanban_examples:visible").toHaveCount(1, {
        message: "should have a link to see examples",
    });

    // click to see the examples
    await contains(".o_column_quick_create .o_kanban_examples").click();

    expect(".modal .o_kanban_examples_dialog").toHaveCount(1, {
        message: "should have open the examples dialog",
    });
    expect(".modal .o_notebook_headers li").toHaveCount(2, {
        message: "should have two examples (in the menu)",
    });
    expect(".modal .o_notebook_headers").toHaveText("A first example\nA second example", {
        message: "example names should be correct",
    });
    expect(".modal .o_notebook_content .tab-pane").toHaveCount(1, {
        message: "should have only rendered one page",
    });

    const firstPane = queryFirst(".modal .o_notebook_content .tab-pane");
    expect(queryAll(".o_kanban_examples_group", { root: firstPane })).toHaveCount(3);
    expect(queryAllTexts("h6", { root: firstPane })).toEqual(["Column 1", "Column 2", "Column 3"], {
        message: "column titles should be correct",
    });
    expect(queryFirst(".o_kanban_examples_description", { root: firstPane })).toHaveInnerHTML(
        "A weak description.",
        { message: "An escaped description should be displayed" }
    );

    await contains(".nav-item:nth-child(2) .nav-link").click();
    const secondPane = queryFirst(".o_notebook_content");
    expect(queryAll(".o_kanban_examples_group", { root: firstPane })).toHaveCount(2);
    expect(queryAllTexts("h6", { root: secondPane })).toEqual(["Col 1", "Col 2"], {
        message: "column titles should be correct",
    });
    expect(secondPane.querySelector(".o_kanban_examples_description").innerHTML).toBe(
        "A fantastic description.",
        { message: "A formatted description should be displayed." }
    );
});

test("quick create column with x_name as _rec_name", async () => {
    Product._rec_name = "x_name";
    Product._fields.x_name = fields.Char();
    Product._records = [
        { id: 3, x_name: "hello" },
        { id: 5, x_name: "xmo" },
    ];

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
    });
    await quickCreateKanbanColumn();
    await editKanbanColumnName("New Column 1");
    await validateKanbanColumn();
    expect(".o_kanban_group").toHaveCount(3, { message: "should now have three columns" });
});

test.tags("desktop");
test("count of folded groups in empty kanban with sample data", async () => {
    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    product_id: [1, "New"],
                    product_id_count: 0,
                    __domain: [],
                },
                {
                    product_id: [2, "In Progress"],
                    product_id_count: 0,
                    __domain: [],
                    __fold: true,
                },
            ],
            length: 2,
        };
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        domain: [["id", "<", 0]],
    });

    expect(queryFirst(".o_content")).toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(queryAllTexts(".o_kanban_group")).toEqual(["New", "In Progress"]);
});

test.tags("desktop");
test("quick create column and examples: with folded columns", async () => {
    registry.category("kanban_examples").add("test", {
        allowedGroupBys: ["product_id"],
        foldField: "folded",
        examples: [
            {
                name: "A first example",
                columns: ["not folded"],
                foldedColumns: ["folded"],
                description: "A weak description.",
            },
        ],
    });
    after(() => registry.category("kanban_examples").remove("test"));

    Partner._records = [];
    Product._fields.folded = fields.Boolean();

    onRpc(["name_create", "write"], ({ model, method, args }) => {
        expect.step(`${method} (model: ${model}):${JSON.stringify(args)}`);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban examples="test">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // the quick create should already be unfolded as there are no records
    expect(".o_column_quick_create .o_quick_create_unfolded").toHaveCount(1);

    // click to see the examples
    await contains(".o_column_quick_create .o_kanban_examples").click();

    // apply the examples
    expect.verifySteps([]);
    await contains(".modal .modal-footer .btn.btn-primary").click();
    expect.verifySteps([
        'name_create (model: product):["not folded"]',
        'name_create (model: product):["folded"]',
        'write (model: product):[[7],{"folded":true}]',
    ]);

    // the applied examples should be visible
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:not(.o_column_folded)").toHaveCount(1);
    expect(".o_kanban_group.o_column_folded").toHaveCount(1);
    expect(queryAllTexts(".o_kanban_group")).toEqual(["not folded\n(0)", "folded"]);
});

test.tags("desktop");
test("quick create column's apply button's display text", async () => {
    const applyExamplesText = "Use This For My Test";
    registry.category("kanban_examples").add("test", {
        allowedGroupBys: ["product_id"],
        applyExamplesText: applyExamplesText,
        examples: [
            {
                name: "A first example",
                columns: ["Column 1", "Column 2", "Column 3"],
            },
            {
                name: "A second example",
                columns: ["Col 1", "Col 2"],
            },
        ],
    });
    after(() => registry.category("kanban_examples").remove("test"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban examples="test">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    // open the quick create
    await quickCreateKanbanColumn();

    // click to see the examples
    await contains(".o_column_quick_create .o_kanban_examples").click();

    expect(".modal footer.modal-footer button.btn-primary").toHaveText(applyExamplesText, {
        message: "the primary button should display the value of applyExamplesText",
    });
});

test.tags("desktop");
test("create column and examples background with ghostColumns titles", async () => {
    registry.category("kanban_examples").add("test", {
        allowedGroupBys: ["product_id"],
        ghostColumns: ["Ghost 1", "Ghost 2", "Ghost 3", "Ghost 4"],
        examples: [
            {
                name: "A first example",
                columns: ["Column 1", "Column 2", "Column 3"],
            },
            {
                name: "A second example",
                columns: ["Col 1", "Col 2"],
            },
        ],
    });
    after(() => registry.category("kanban_examples").remove("test"));

    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban examples="test">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_example_background").toHaveCount(1, {
        message: "should have ExamplesBackground when no data",
    });
    expect(queryAllTexts(".o_kanban_examples_group h6")).toEqual([
        "Ghost 1",
        "Ghost 2",
        "Ghost 3",
        "Ghost 4",
    ]);
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a ColumnQuickCreate widget",
    });
    expect(".o_column_quick_create .o_kanban_examples:visible").toHaveCount(1, {
        message: "should not have a link to see examples as there is no examples registered",
    });
});

test("create column and examples background without ghostColumns titles", async () => {
    Partner._records = [];

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
    });

    expect(".o_kanban_example_background").toHaveCount(1, {
        message: "should have ExamplesBackground when no data",
    });
    expect(queryAllTexts(".o_kanban_examples_group h6")).toEqual([
        "Column 1",
        "Column 2",
        "Column 3",
        "Column 4",
    ]);
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a ColumnQuickCreate widget",
    });
    expect(".o_column_quick_create .o_kanban_examples:visible").toHaveCount(0, {
        message: "should not have a link to see examples as there is no examples registered",
    });
});

test("nocontent helper after adding a record (kanban with progressbar)", async () => {
    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "hello"],
                },
            ],
        };
    });
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban >
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        domain: [["foo", "=", "abcd"]],
        noContentHelp: "No content helper",
    });

    expect(".o_view_nocontent").toHaveCount(1, { message: "the nocontent helper is displayed" });

    // add a record
    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "twilight sparkle");
    await validateKanbanRecord();

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "the nocontent helper is not displayed after quick create",
    });

    // cancel quick create
    await discardKanbanRecord();
    expect(".o_view_nocontent").toHaveCount(0, {
        message: "the nocontent helper is not displayed after cancelling the quick create",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "onchange",
        "name_create",
        "web_read",
        "read_progress_bar",
        "web_read_group",
        "onchange",
    ]);
});

test.tags("desktop");
test("ungrouped kanban view can be grouped, then ungrouped", async () => {
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
        searchViewArch: `
            <search>
                <filter name="group_by_product" domain="[]" string="GroupBy Product" context="{ 'group_by': 'product_id' }"/>
            </search>`,
    });

    expect(".o_kanban_renderer").not.toHaveClass("o_kanban_grouped");

    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Product");

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");

    await toggleMenuItem("GroupBy Product");

    expect(".o_kanban_renderer").not.toHaveClass("o_kanban_grouped");
});

test("no content helper when archive all records in kanban group", async () => {
    // add active field on partner model to have archive option
    Partner._fields.active = fields.Boolean({ default: true });
    // remove last records to have only one column
    Partner._records = Partner._records.slice(0, 3);

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
        noContentHelp: '<p class="hello">click to add a partner</p>',
        groupBy: ["bar"],
    });

    // check that the (unique) column contains 3 records
    expect(".o_kanban_group:last-child .o_kanban_record").toHaveCount(3);

    // archive the records of the last column
    const clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Archive All");

    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog footer .btn-primary").click();

    // check no content helper is exist
    expect(".o_view_nocontent").toHaveCount(1);
});

test.tags("desktop");
test("no content helper when no data", async () => {
    Partner._records = [];

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
        noContentHelp: '<p class="hello">click to add a partner</p>',
    });

    expect(".o_view_nocontent").toHaveCount(1, { message: "should display the no content helper" });

    expect(".o_view_nocontent").toHaveText('<p class="hello">click to add a partner</p>', {
        message: "should have rendered no content helper from action",
    });

    MockServer.env["partner"].create([{ foo: "new record" }]);
    await press("Enter");
    await animationFrame();

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "should not display the no content helper",
    });
});

test("no nocontent helper for grouped kanban with empty groups", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        for (const group of result.groups) {
            group[kwargs.groupby[0] + "_count"] = 0;
        }
        return result;
    });

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

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be two columns" });
    expect(".o_kanban_record").toHaveCount(0, { message: "there should be no records" });
});

test("no nocontent helper for grouped kanban with no records", async () => {
    Partner._records = [];

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

    expect(".o_kanban_group").toHaveCount(0, { message: "there should be no columns" });
    expect(".o_kanban_record").toHaveCount(0, { message: "there should be no records" });
    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (we are in 'column creation mode')",
    });
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "there should be a column quick create",
    });
});

test("no nocontent helper is shown when no longer creating column", async () => {
    Partner._records = [];

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

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (we are in 'column creation mode')",
    });

    // creating a new column
    await editKanbanColumnName("applejack");
    await validateKanbanColumn();

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (still in 'column creation mode')",
    });

    // leaving column creation mode
    await press("Escape");
    await animationFrame();

    expect(".o_view_nocontent").toHaveCount(1, { message: "there should be a nocontent helper" });
});

test("no nocontent helper is hidden when quick creating a column", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "hello"],
                },
            ],
            length: 1,
        };
    });

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

    await quickCreateKanbanColumn();

    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should be no nocontent helper (we are in 'column creation mode')",
    });
});

test("remove nocontent helper after adding a record", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "hello"],
                },
            ],
            length: 1,
        };
    });

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

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "hello"],
                },
            ],
            length: 1,
        };
    });

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

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "hello"],
                },
            ],
            length: 1,
        };
    });

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

test("nocontent helper for grouped kanban (on m2o field) with no records with no group_create", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban group_create="false">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        noContentHelp: "No content helper",
    });

    expect(".o_kanban_group").toHaveCount(0, { message: "there should be no columns" });
    expect(".o_kanban_record").toHaveCount(0, { message: "there should be no records" });
    expect(".o_view_nocontent").toHaveCount(0, {
        message: "there should not be a nocontent helper",
    });
    expect(".o_column_quick_create").toHaveCount(0, {
        message: "there should not be a column quick create",
    });
});

test("nocontent helper for grouped kanban (on date field) with no records with no group_create", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban group_create="false">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["date"],
        noContentHelp: "No content helper",
    });

    expect(".o_kanban_group").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_column_quick_create").toHaveCount(0);
    expect(".o_kanban_example_background").toHaveCount(0);
});

test("empty grouped kanban with sample data and no columns", async () => {
    Partner._records = [];

    await mountView({
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        resModel: "partner",
        type: "kanban",
        noContentHelp: "No content helper",
    });

    expect(".o_view_nocontent").toHaveCount(0);
    expect(".o_quick_create_unfolded").toHaveCount(1);
    expect(".o_kanban_example_background_container").toHaveCount(1);
});

test("empty kanban with sample data grouped by date range (fill temporal)", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => {
        // Simulate fill temporal
        return {
            groups: [
                {
                    date_count: 0,
                    state: false,
                    "date:month": "December 2022",
                    __range: {
                        "date:month": {
                            from: "2022-12-01",
                            to: "2023-01-01",
                        },
                    },
                    __domain: [
                        ["date", ">=", "2022-12-01"],
                        ["date", "<", "2023-01-01"],
                    ],
                },
            ],
            length: 1,
        };
    });
    await mountView({
        arch: `
            <kanban sample="1">
                <progressbar field="state" sum_field="int_field" help="progress" colors="{}"/>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["date:month"],
        resModel: "partner",
        type: "kanban",
        noContentHelp: "No content helper",
    });

    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_kanban_group .o_column_title").toHaveText("December 2022");
    expect(".o_kanban_group").toHaveCount(1);
    expect(".o_kanban_group .o_kanban_record").toHaveCount(16);
});

test("empty grouped kanban with sample data and click quick create", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group[`${kwargs.groupby[0]}_count`] = 0;
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

test.tags("desktop");
test("quick create record in grouped kanban with sample data", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group[`${kwargs.groupby[0]}_count`] = 0;
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

test("empty grouped kanban with sample data and cancel quick create", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        result.groups.forEach((group) => {
            group[`${kwargs.groupby[0]}_count`] = 0;
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
test("empty grouped kanban with sample data: keynav", async () => {
    onRpc("web_read_group", function ({ parent }) {
        const result = parent();
        result.groups.forEach((g) => (g.product_id_count = 0));
        return result;
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <field name="state" widget="priority"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_record").toHaveCount(16);
    expect(document.activeElement).toHaveClass("o_searchview_input");

    await press("ArrowDown");
    await animationFrame();

    expect(document.activeElement).toHaveClass("o_searchview_input");
});

test.tags("desktop");
test("empty kanban with sample data", async () => {
    Partner._records = [];

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
        searchViewArch: `
            <search>
                <filter name="no_match" string="Match nothing" domain="[['id', '=', 0]]"/>
            </search>`,
        noContentHelp: "No content helper",
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(10, {
        message: "there should be 10 sample records",
    });
    expect(".o_view_nocontent").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("Match nothing");

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(1);
});

test("empty grouped kanban with sample data and many2many_tags", async () => {
    onRpc("web_read_group", function ({ kwargs, parent }) {
        const result = parent();
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        result.groups.forEach((group) => {
            group[`${kwargs.groupby[0]}_count`] = 0;
        });
        return result;
    });
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban sample="1">
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                        <field name="category_ids" widget="many2many_tags"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be 2 'real' columns" });
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(queryAll(".o_kanban_record").length >= 1).toBe(true, {
        message: "there should be sample records",
    });
    expect(queryAll(".o_field_many2many_tags .o_tag").length >= 1).toBe(true, {
        message: "there should be tags",
    });
    // should not read the tags
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
    ]);
});

test.tags("desktop");
test("sample data does not change after reload with sample data", async () => {
    Partner._views["kanban,false"] = `
        <kanban sample="1">
            <templates>
                <t t-name="card">
                    <field name="int_field"/>
                </t>
            </templates>
        </kanban>`;
    Partner._views["search,false"] = "<search/>";
    // list-view so that there is a view switcher, unused
    Partner._views["list,false"] = '<list><field name="foo"/></list>';

    onRpc("web_read_group", function ({ kwargs, parent }) {
        const result = parent();
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        result.groups.forEach((group) => {
            group[`${kwargs.groupby[0]}_count`] = 0;
        });
        return result;
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "list"],
        ],
        context: {
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_group").toHaveCount();
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_record").toHaveCount(16);

    const kanbanText = queryText(".o_kanban_view");
    await contains(".o_control_panel .o_switch_view.o_kanban").click();

    expect(".o_kanban_view").toHaveText(kanbanText, {
        message: "the content should be the same after reloading the view",
    });
});

test.tags("desktop");
test("non empty kanban with sample data", async () => {
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
        searchViewArch: `
            <search>
                <filter name="no_match" string="Match nothing" domain="[['id', '=', 0]]"/>
            </search>`,
        noContentHelp: "No content helper",
    });

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);
    expect(".o_view_nocontent").toHaveCount(0);

    await toggleSearchBarMenu();
    await toggleMenuItem("Match nothing");

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(0);
});

test("empty grouped kanban with sample data: add a column", async () => {
    onRpc("web_read_group", function ({ parent }) {
        const result = parent();
        result.groups = Product._records.map((r) => {
            return {
                product_id: [r.id, r.display_name],
                product_id_count: 0,
                __domain: [["product_id", "=", r.id]],
            };
        });
        result.length = result.groups.length;
        return result;
    });

    await mountView({
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        resModel: "partner",
        type: "kanban",
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });

    await quickCreateKanbanColumn();
    await editKanbanColumnName("Yoohoo");
    await validateKanbanColumn();

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(3);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });
});

test.tags("desktop");
test("empty grouped kanban with sample data: cannot fold a column", async () => {
    // folding a column in grouped kanban with sample data is disabled, for the sake of simplicity
    onRpc("web_read_group", function ({ kwargs, parent }) {
        const result = parent();
        // override read_group to return a single, empty group
        result.groups = result.groups.slice(0, 1);
        result.groups[0][`${kwargs.groupby[0]}_count`] = 0;
        result.length = 1;
        return result;
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(1);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });

    await toggleKanbanColumnActions(0);

    expect(getDropdownMenu(".o_kanban_config").querySelector(".o_kanban_toggle_fold")).toHaveClass(
        "disabled"
    );
});

test("empty grouped kanban with sample data: delete a column", async () => {
    Partner._records = [];

    let groups = [
        {
            product_id: [1, "New"],
            product_id_count: 0,
            __domain: [],
        },
    ];

    onRpc("web_read_group", () => {
        // override read_group to return a single, empty group
        return {
            groups,
            length: groups.length,
        };
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(1);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });

    // Delete the first column
    groups = [];
    const clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Delete");
    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_kanban_group").toHaveCount(0);
    expect(".o_column_quick_create .o_quick_create_unfolded").toHaveCount(1);
});

test("empty grouped kanban with sample data: add a column and delete it right away", async () => {
    onRpc("web_read_group", function ({ parent }) {
        const result = parent();
        result.groups = Product._records.map((r) => {
            return {
                product_id: [r.id, r.display_name],
                product_id_count: 0,
                __domain: [["product_id", "=", r.id]],
            };
        });
        result.length = result.groups.length;
        return result;
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });

    // add a new column
    await quickCreateKanbanColumn();
    await editKanbanColumnName("Yoohoo");
    await validateKanbanColumn();

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(3);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });

    // delete the column we just created
    const clickColumnAction = await toggleKanbanColumnActions(2);
    await clickColumnAction("Delete");
    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record").length > 0).toBe(true, {
        message: "should contain sample records",
    });
});

test.tags("desktop");
test("kanban with sample data: do an on_create action", async () => {
    Partner._records = [];
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    onRpc("/web/action/load", () => {
        return {
            type: "ir.actions.act_window",
            name: "Archive Action",
            res_model: "partner",
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
        };
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1" on_create="myCreateAction">
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                    </div>
                </templates>
            </kanban>`,
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(10, {
        message: "there should be 10 sample records",
    });
    expect(".o_view_nocontent").toHaveCount(1);

    await createKanbanRecord();
    expect(".modal").toHaveCount(1);

    await contains(".modal .o_form_button_save").click();
    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
});

test("kanban with sample data grouped by m2o and existing groups", async () => {
    Partner._records = [];

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    product_id_count: 0,
                    product_id: [3, "hello"],
                    __domain: [["product_id", "=", "3"]],
                },
            ],
            length: 2,
        };
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="product_id"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_kanban_group:first .o_column_title").toHaveText("hello");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(16);
    expect(".o_kanban_record").toHaveText("hello");
});

test.tags("desktop");
test("bounce create button when no data and click on empty area", async () => {
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
        searchViewArch: `
            <search>
                <filter name="no_match" string="Match nothing" domain="[['id', '=', 0]]"/>
            </search>`,
        noContentHelp: "click to add a partner",
    });

    await contains(".o_kanban_view").click();
    expect(".o-kanban-button-new").not.toHaveClass("o_catch_attention");

    await toggleSearchBarMenu();
    await toggleMenuItem("Match nothing");

    await contains(".o_kanban_renderer").click();
    expect(".o-kanban-button-new").toHaveClass("o_catch_attention");
});

test("buttons with modifiers", async () => {
    Partner._records[1].bar = false; // so that test is more complete

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <field name="bar"/>
                <field name="state"/>
                <templates>
                    <div t-name="card">
                        <button class="o_btn_test_1" type="object" name="a1" invisible="foo != 'yop'"/>
                        <button class="o_btn_test_2" type="object" name="a2" invisible="bar and state not in ['abc', 'def']"/>
                    </div>
                </templates>
            </kanban>`,
    });

    expect(".o_btn_test_1").toHaveCount(1, { message: "kanban should have one buttons of type 1" });
    expect(".o_btn_test_2").toHaveCount(3, {
        message: "kanban should have three buttons of type 2",
    });
});

test("support styling of anchor tags with action type", async function (assert) {
    expect.assertions(3);

    mockService("action", {
        doActionButton(action) {
            expect(action.name).toBe("42");
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <a type="action" name="42" class="btn-primary" style="margin-left: 10px"><i class="oi oi-arrow-right"/> Click me !</a>
                    </div>
                </templates>
            </kanban>`,
    });

    await click("a[type='action']");
    expect("a[type='action']:first").toHaveClass("btn-primary");
    expect(queryFirst("a[type='action']").style.marginLeft).toBe("10px");
});

test("button executes action and reloads", async () => {
    stepAllNetworkCalls();

    let count = 0;
    mockService("action", {
        async doActionButton({ onClose }) {
            count++;
            await animationFrame();
            onClose();
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <button type="object" name="a1" class="a1">
                            A1
                        </button>
                    </div>
                </templates>
            </kanban>`,
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);
    expect("button.a1").toHaveCount(4);
    expect("button.a1:first").not.toHaveAttribute("disabled");

    await click("button.a1");

    expect("button.a1:first").toHaveAttribute("disabled");

    await animationFrame();

    expect("button.a1:first").not.toHaveAttribute("disabled");
    expect(count).toBe(1, { message: "should have triggered an execute action only once" });
    // the records should be reloaded after executing a button action
    expect.verifySteps(["web_search_read"]);
});

test("button executes action and check domain", async () => {
    Partner._fields.active = fields.Boolean({ default: true });
    for (let i = 0; i < Partner.length; i++) {
        Partner._records[i].active = true;
    }

    mockService("action", {
        doActionButton({ onClose }) {
            Partner._records[0].active = false;
            onClose();
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <button type="object" name="a1" />
                        <button type="object" name="action_archive" class="action-archive" />
                    </div>
                </templates>
            </kanban>`,
    });

    expect(queryText("span", { root: getKanbanRecord({ index: 0 }) })).toBe("yop", {
        message: "should display 'yop' record",
    });
    await contains("button.action-archive", { root: getKanbanRecord({ index: 0 }) }).click();
    expect(queryText("span", { root: getKanbanRecord({ index: 0 }) })).not.toBe("yop", {
        message: "should have removed 'yop' record from the view",
    });
});

test("field tag with modifiers but no widget", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" invisible="id == 1"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:first").toHaveText("");
    expect(".o_kanban_record:eq(1)").toHaveText("blip");
});

test("field tag with widget and class attributes", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="char" class="hi"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_field_widget.hi").toHaveCount(4);
});

test("rendering date and datetime (value)", async () => {
    Partner._records[0].date = "2017-01-25";
    Partner._records[1].datetime = "2016-12-12 10:55:05";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field class="date" name="date"/>
                        <field class="datetime" name="datetime"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 0 }).querySelector(".date")).toHaveText("01/25/2017");
    expect(getKanbanRecord({ index: 1 }).querySelector(".datetime")).toHaveText(
        "12/12/2016 11:55:05"
    );
});

test("rendering date and datetime (raw value)", async () => {
    Partner._records[0].date = "2017-01-25";
    Partner._records[1].datetime = "2016-12-12 10:55:05";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="date"/>
                <field name="datetime"/>
                <templates>
                    <t t-name="card">
                        <span class="date" t-esc="record.date.raw_value"/>
                        <span class="datetime" t-esc="record.datetime.raw_value"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 0 }).querySelector(".date")).toHaveText(
        "2017-01-25T00:00:00.000+01:00"
    );
    expect(getKanbanRecord({ index: 1 }).querySelector(".datetime")).toHaveText(
        "2016-12-12T11:55:05.000+01:00"
    );
});

test("rendering many2one (value)", async () => {
    Partner._records[1].product_id = false;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="product_id" class="product_id"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual(["hello", "", "hello", "xmo"]);
});

test("rendering many2one (raw value)", async () => {
    Partner._records[1].product_id = false;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="product_id"/>
                <templates>
                    <t t-name="card">
                        <span class="product_id" t-esc="record.product_id.raw_value"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual(["3", "false", "3", "5"]);
});

test("evaluate conditions on relational fields", async () => {
    Partner._records[0].product_id = false;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="product_id"/>
                <field name="category_ids"/>
                <templates>
                    <t t-name="card">
                        <button t-if="!record.product_id.raw_value" class="btn_a">A</button>
                        <button t-if="!record.category_ids.raw_value.length" class="btn_b">B</button>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4, {
        message: "there should be 4 records",
    });
    expect(".o_kanban_record:not(.o_kanban_ghost) .btn_a").toHaveCount(1, {
        message: "only 1 of them should have the 'Action' button",
    });
    expect(".o_kanban_record:not(.o_kanban_ghost) .btn_b").toHaveCount(2, {
        message: "only 2 of them should have the 'Action' button",
    });
});

test.tags("desktop");
test("resequence columns in grouped by m2o", async () => {
    Product._fields.sequence = fields.Integer();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("hello\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    await contains(".o_kanban_group:first-child").dragAndDrop(".o_kanban_group:nth-child(2)");

    // Drag & drop on column (not title) should not work
    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("hello\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    await contains(".o_kanban_group:first-child .o_column_title").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("xmo\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["2", "4", "1", "3"]);
});

test.tags("desktop");
test("resequence all when creating new record + partial resequencing", async () => {
    let resequenceOffset;
    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        const { ids, offset } = params;
        expect.step({ ids, ...(offset ? { offset } : {}) });
        resequenceOffset = offset || 0;
        return true;
    });
    onRpc("read", ({ args }) => {
        // Important to simulate the server returning the new sequence.
        const [ids, fields] = args;
        return ids.map((id, index) => ({
            id,
            [fields[0]]: resequenceOffset + index,
        }));
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    await quickCreateKanbanColumn();
    await editKanbanColumnName("foo");
    await validateKanbanColumn();
    expect.verifySteps([{ ids: [3, 5, 6] }]);

    await editKanbanColumnName("bar");
    await validateKanbanColumn();
    expect.verifySteps([{ ids: [3, 5, 6, 7] }]);

    await editKanbanColumnName("baz");
    await validateKanbanColumn();
    expect.verifySteps([{ ids: [3, 5, 6, 7, 8] }]);

    await editKanbanColumnName("boo");
    await validateKanbanColumn();
    expect.verifySteps([{ ids: [3, 5, 6, 7, 8, 9] }]);

    // When rearranging, only resequence the affected records. In this example,
    // dragging column 2 to column 4 should only resequence [5, 6, 7] to [6, 7, 5]
    // with offset 1.
    await contains(".o_kanban_group:nth-child(2) .o_column_title").dragAndDrop(
        ".o_kanban_group:nth-child(4)"
    );
    expect.verifySteps([{ ids: [6, 7, 5], offset: 1 }]);
});

test("prevent resequence columns if groups_draggable=false", async () => {
    Product._fields.sequence = fields.Integer();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban groups_draggable='0'>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("hello\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    await contains(".o_kanban_group:first-child").dragAndDrop(".o_kanban_group:nth-child(2)");

    // Drag & drop on column (not title) should not work
    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("hello\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    await contains(".o_kanban_group:first-child .o_column_title").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(getKanbanColumn(0).querySelector(".o_column_title")).toHaveText("hello\n(2)");
    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);
});

test("open config dropdown on kanban with records and groups draggable off", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban groups_draggable='0' records_draggable='0'>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group .o_kanban_config").toHaveCount(2);
    expect(".o-dropdown--menu").toHaveCount(0);

    await toggleKanbanColumnActions(0);

    expect(".o-dropdown--menu").toHaveCount(1);
});

test("properly evaluate more complex domains", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="bar"/>
                <field name="category_ids"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <button type="object" invisible="bar or category_ids" class="btn btn-primary float-end" name="arbitrary">Join</button>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("button.float-end.oe_kanban_action").toHaveCount(1, {
        message: "only one button should be visible",
    });
});

test("kanban with color attribute", async () => {
    Category._records[0].color = 5;
    Category._records[1].color = 6;

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban highlight_color="color">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_5");
    expect(getKanbanRecord({ index: 1 })).toHaveClass("o_kanban_color_6");
});

test("edit the kanban color with the colorpicker", async () => {
    Category._records[0].color = 12;

    onRpc("web_save", ({ args }) => {
        expect.step(`write-color-${args[1].color}`);
    });

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban highlight_color="color">
                <templates>
                    <t t-name="menu">
                        <field name="color" widget="kanban_color_picker"/>
                    </t>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);

    expect(".o_kanban_record.o_kanban_color_12").toHaveCount(0, {
        message: "no record should have the color 12",
    });
    expect(
        queryAll(".o_kanban_colorpicker", { root: getDropdownMenu(getKanbanRecord({ index: 0 })) })
    ).toHaveCount(1);
    expect(
        queryAll(".o_kanban_colorpicker > *", {
            root: getDropdownMenu(getKanbanRecord({ index: 0 })),
        })
    ).toHaveCount(12, { message: "the color picker should have 12 children (the colors)" });

    await contains(".o_kanban_colorpicker a.o_kanban_color_9").click();

    // should write on the color field
    expect.verifySteps(["write-color-9"]);
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_9");
});

test("kanban with colorpicker and node with color attribute", async () => {
    Category._fields.colorpickerField = fields.Integer();
    Category._records[0].colorpickerField = 3;

    onRpc("web_save", ({ args }) => {
        expect.step(`write-color-${args[1].colorpickerField}`);
    });

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban highlight_color="colorpickerField">
                <templates>
                    <t t-name="menu">
                        <field name="colorpickerField" widget="kanban_color_picker"/>
                    </t>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_3");
    await toggleKanbanRecordDropdown(0);
    await contains(`.o_kanban_colorpicker li[title="Raspberry"] a.o_kanban_color_9`).click();
    // should write on the color field
    expect.verifySteps(["write-color-9"]);
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_9");
});

test("edit the kanban color with translated colors resulting in the same terms", async () => {
    Category._records[0].color = 12;

    const translations = {
        Purple: "Violet",
        Violet: "Violet",
    };
    defineParams({ translations });

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban highlight_color="color">
                <templates>
                    <t t-name="menu">
                        <field name="color" widget="kanban_color_picker"/>
                    </t>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);
    await contains(".o_kanban_colorpicker a.o_kanban_color_9").click();
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_9");
});

test("colorpicker doesn't appear when missing access rights", async () => {
    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban edit="0">
                <templates>
                    <t t-name="menu">
                        <field name="color" widget="kanban_color_picker"/>
                    </t>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);
    expect(".o_kanban_colorpicker").toHaveCount(0);
});

test("load more records in column", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`${kwargs.limit} - ${kwargs.offset}`);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        limit: 2,
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2, {
        message: "there should be 2 records in the column",
    });
    expect(getKanbanRecordTexts(1)).toEqual(["1", "2"]);

    // load more
    await clickKanbanLoadMore(1);

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3, {
        message: "there should now be 3 records in the column",
    });
    // the records should be correctly fetched
    expect.verifySteps(["2 - 0", "2 - 0", "4 - 0"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1", "2", "3"]);

    // reload
    await validateSearch();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3, {
        message: "there should still be 3 records in the column after reload",
    });
    expect(getKanbanRecordTexts(1)).toEqual(["1", "2", "3"]);
    expect.verifySteps(["2 - 0", "4 - 0"]);
});

test("load more records in column with x2many", async () => {
    Partner._records[0].category_ids = [7];
    Partner._records[1].category_ids = [];
    Partner._records[2].category_ids = [6];
    Partner._records[3].category_ids = [];
    // record [2] will be loaded after

    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read ${kwargs.limit}-${kwargs.offset}`);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="category_ids"/>
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        limit: 2,
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(queryAllTexts("[name='category_ids']", { root: getKanbanColumn(1) })).toEqual([
        "silver",
        "",
    ]);
    expect.verifySteps(["web_search_read 2-0", "web_search_read 2-0"]);

    // load more
    await clickKanbanLoadMore(1);

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(3);
    expect(queryAllTexts("[name='category_ids']", { root: getKanbanColumn(1) })).toEqual([
        "silver",
        "",
        "gold",
    ]);
    expect.verifySteps(["web_search_read 4-0"]);
});

test("update buttons after column creation", async () => {
    Partner._records = [];

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
    });

    expect(".o-kanban-button-new").toHaveCount(0);

    await editKanbanColumnName("new column");
    await validateKanbanColumn();

    expect(".o_control_panel_main_buttons button.o-kanban-button-new").toHaveCount(1);
});

test.tags("desktop");
test("group_by_tooltip option when grouping on a many2one", async () => {
    Partner._records[3].product_id = false;

    onRpc("read", ({ args }) => {
        expect.step("read: product");
        expect(args[1]).toEqual(["display_name", "name"], {
            message: "should read on specified fields on the group by relation",
        });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="bar">
                <field name="product_id" options='{"group_by_tooltip": {"name": "Kikou"}}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="group_by_product_id" domain="[]" string="GroupBy Product" context="{ 'group_by': 'product_id' }"/>
            </search>`,
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group").toHaveCount(2, { message: "should have 2 columns" });

    // simulate an update coming from the searchview, with another groupby given
    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy Product");

    expect(".o_kanban_group").toHaveCount(3, { message: "should have 3 columns" });
    expect(".o_kanban_group:first").toHaveClass("o_column_folded");

    await contains(".o_kanban_group").click();
    expect(".o_kanban_group").toHaveCount(3, { message: "should have 3 columns" });
    expect(".o_kanban_group:first").not.toHaveClass("o_column_folded");
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(2) })).toHaveCount(1);
    expect(queryText(".o_column_title", { root: getKanbanColumn(0) })).toBe("None\n(1)", {
        message: "first column should have a default title for when no value is provided",
    });

    await hover(".o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(0, {
        message:
            "tooltip of first column should not defined, since group_by_tooltip title and the many2one field has no value",
    });
    // should not have done any read on product because no value
    expect.verifySteps([]);

    await hover(".o_column_title:eq(1)");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(1, {
        message:
            "second column should have a tooltip with the group_by_tooltip title and many2one field value",
    });
    expect(".o-tooltip:first").toHaveText("Kikou\nhello");
    expect(".o_kanban_group:nth-child(2) .o_column_title").toHaveText("hello\n(2)", {
        message: "second column should have a title with a value from the many2one",
    });
    // should have done one read on product for the second column tooltip
    expect.verifySteps(["read: product"]);
});

test.tags("desktop");
test("asynchronous tooltips when grouped", async () => {
    const def = new Deferred();
    onRpc("read", () => {
        expect.step("read: product");
        return def;
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id">
                <field name="product_id" options='{"group_by_tooltip": {"name": "Name"}}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_column_title").toHaveCount(2);

    await hover(".o_kanban_group .o_kanban_header_title .o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(0);

    await leave();
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(0);

    await hover(".o_kanban_group .o_kanban_header_title .o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(0);

    def.resolve();
    await animationFrame();

    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveText("Name\nhello");
    expect.verifySteps(["read: product"]);
});

test.tags("desktop");
test("loads data tooltips only when first opening", async () => {
    onRpc("read", () => {
        expect.step("read: product");
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id">
                <field name="product_id" options='{"group_by_tooltip": {"name": "Name"}}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await hover(".o_kanban_group .o_kanban_header_title .o_column_title");
    await await runAllTimers();
    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveText("Name\nhello");
    expect.verifySteps(["read: product"]);

    await leave();
    await animationFrame();
    expect(".o-tooltip").toHaveCount(0, { message: "tooltip should be closed" });

    await hover(".o_kanban_group .o_kanban_header_title .o_column_title");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveText("Name\nhello");
    expect.verifySteps([]);
});

test.tags("desktop");
test("move a record then put it again in the same column", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    await editKanbanColumnName("column1");
    await validateKanbanColumn();

    await editKanbanColumnName("column2");
    await validateKanbanColumn();

    await quickCreateKanbanRecord(1);
    await editKanbanRecordQuickCreateInput("display_name", "new partner");
    await validateKanbanRecord();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);

    await contains(".o_kanban_group:nth-child(2) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first-child"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(0);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
});

test.tags("desktop");
test("resequence a record twice", async () => {
    Partner._records = [];

    const def = new Deferred();
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return def;
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    await editKanbanColumnName("column1");
    await validateKanbanColumn();

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "record1");
    await validateKanbanRecord();

    await quickCreateKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "record2");
    await validateKanbanRecord();
    await discardKanbanRecord(); // close quick create

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(getKanbanRecordTexts()).toEqual(["record2", "record1"], {
        message: "records should be correctly ordered",
    });

    await contains(".o_kanban_record:nth-child(2)").dragAndDrop(".o_kanban_record:nth-child(3)");
    def.resolve();
    await animationFrame();

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(getKanbanRecordTexts()).toEqual(["record1", "record2"], {
        message: "records should be correctly ordered",
    });

    await contains(".o_kanban_record:nth-child(3)").dragAndDrop(".o_kanban_record:nth-child(2)");

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(getKanbanRecordTexts()).toEqual(["record2", "record1"], {
        message: "records should be correctly ordered",
    });
    // should have resequenced twice
    expect.verifySteps(["resequence", "resequence"]);
});

test("basic support for widgets (being Owl Components)", async () => {
    class MyComponent extends Component {
        static template = xml`<div t-att-class="props.class" t-esc="value"/>`;
        static props = ["*"];
        get value() {
            return JSON.stringify(this.props.record.data);
        }
    }
    const myComponent = {
        component: MyComponent,
    };
    viewWidgetRegistry.add("test", myComponent);
    after(() => viewWidgetRegistry.remove("test"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <widget name="test"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 2 }).querySelector(".o_widget")).toHaveText('{"foo":"gnap"}');
});

test("kanban card: record value should be updated", async () => {
    class MyComponent extends Component {
        static template = xml`<div><button t-on-click="onClick">CLick</button></div>`;
        static props = ["*"];
        onClick() {
            this.props.record.update({ foo: "yolo" });
        }
    }
    const myComponent = {
        component: MyComponent,
    };
    viewWidgetRegistry.add("test", myComponent);
    after(() => viewWidgetRegistry.remove("test"));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" class="foo"/>
                        <widget name="test"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryText(".foo", { root: getKanbanRecord({ index: 0 }) })).toBe("yop");

    await click(queryOne("button", { root: getKanbanRecord({ index: 0 }) }));
    await animationFrame();
    await animationFrame();

    expect(queryText(".foo", { root: getKanbanRecord({ index: 0 }) })).toBe("yolo");
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
        "web_search_read",
        "web_search_read",
    ]);
});

test("filter on progressbar in new groups", async () => {
    Partner._views["form,some_view_ref"] = `<form><field name="foo"/></form>`;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create" quick_create_view="some_view_ref">
                <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
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
        "web_search_read",
        "web_search_read",
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
        "web_search_read",
        "web_search_read",
        "web_read_group",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
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
    ]);
});

test("column progressbars: creating a new column should create a new progressbar", async () => {
    stepAllNetworkCalls();
    // // FIXME: use stepAllNetworkCalls when fixed in hoot (return true/false)
    // onRpc(({ method }) => {
    //     expect.step(method);
    // });
    // onRpc("/web/dataset/resequence", () => {
    //     expect.step("/web/dataset/resequence");
    // });

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
        groupBy: ["product_id"],
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
        "web_search_read",
        "web_search_read",
        "name_create",
        "/web/dataset/resequence",
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
        "web_search_read",
        "web_search_read",
        "onchange",
        "name_create",
        "web_read",
        "read_progress_bar",
        "onchange",
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
        "web_search_read",
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
        "web_search_read",
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
    });

    expect(getKanbanCounters()).toEqual(["-4", "36"]);
    expect(getKanbanColumnTooltips(1)).toEqual(["1 yop", "1 gnap", "1 blip"], {
        message: "the counter progressbars should be correctly displayed",
    });

    // archive all records of the second columns
    const clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Archive All");
    await contains(".o_dialog footer .btn-primary").click(); // confirm

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
        "web_search_read",
        "web_search_read",
        "action_archive",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
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
    });

    expect(getKanbanRecordTexts()).toEqual(["4", "1", "2", "3"]);

    // archive all records of the first column
    const clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Archive All");
    await contains(".o_dialog footer .btn-primary").click(); // confirm

    expect(getKanbanRecordTexts()).toEqual(["1", "2", "3"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "action_archive",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
    ]);
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
        "web_search_read",
        "web_search_read",
        // reload
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test("RPCs when (de)activating kanban view progressbar filters", async () => {
    stepAllNetworkCalls();
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(`web_read_group domain ${JSON.stringify(kwargs.domain)}`);
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
        "web_read_group domain []",
        "web_search_read",
        "web_search_read",
        "web_read_group", // recomputes aggregates
        "web_search_read",
        'web_read_group domain ["&",["bar","=",true],["foo","=","yop"]]', // perform read_group only on second column (bar=true)
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "web_read_group domain []",
        'web_read_group domain ["&",["bar","=",true],["foo","=","yop"]]',
        // activate filter
        "web_read_group", // recomputes aggregates
        "web_search_read",
        'web_read_group domain ["&",["bar","=",true],["foo","=","gnap"]]', // perform read_group only on second column (bar=true)
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "web_read_group domain []",
        'web_read_group domain ["&",["bar","=",true],["foo","=","gnap"]]',
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
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "web_save",
        "read_progress_bar",
        "/web/dataset/resequence",
        "read",
        "web_save",
        "read_progress_bar",
        "/web/dataset/resequence",
        "read",
        "web_save",
        "read_progress_bar",
        "/web/dataset/resequence",
        "read",
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
        "web_search_read",
        "web_search_read",
        "web_save",
        "read_progress_bar",
        "web_read_group",
        "/web/dataset/resequence",
        "read",
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
        "web_search_read",
        "web_search_read",
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
        "web_search_read",
        "web_search_read",
        "web_save",
        "read_progress_bar",
        "/web/dataset/resequence",
        "read",
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
        "web_search_read",
        "web_search_read",
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
    expect.verifySteps(["read_progress_bar", "web_read_group", "web_search_read"]);
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
        "web_search_read",
        "web_search_read",
    ]);

    await contains(".progress-bar.bg-success", { root: getKanbanColumn(1) }).click();

    expect(getKanbanColumnTooltips()).toEqual(["1 blip", "4 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["-4", "610"]);
    expect.verifySteps([
        "web_read_group", // recomputes aggregates
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
    ]);

    // Add searchdomain to something restricting progressbars' values (records still in filtered group)
    await toggleSearchBarMenu();
    await toggleMenuItem("My filter");

    expect(getKanbanColumnTooltips()).toEqual(["3 yop"]);
    expect(getKanbanCounters()).toEqual(["600"]);
    expect.verifySteps(["read_progress_bar", "web_read_group", "web_search_read"]);
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
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
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

test("progress bar with aggregates: Archive All in a column", async () => {
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
    });

    expect(getKanbanColumnTooltips(1)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["268", "15"]);

    const clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Archive All");

    expect(".o_dialog").toHaveCount(1);
    def = new Deferred();
    await contains(".o_dialog footer .btn-primary").click();

    expect(getKanbanColumnTooltips(1)).toEqual(["2 yop", "1 gnap", "1 blip"]);
    expect(getKanbanCounters()).toEqual(["268", "15"]);

    def.resolve();
    await animationFrame();

    expect(getKanbanColumnTooltips(1)).toEqual([]);
    expect(getKanbanCounters()).toEqual(["268", "0"]);
});

test.tags("desktop");
test("load more should load correct records after drag&drop event", async () => {
    Partner._order = ["sequence", "id"];
    Partner._records.forEach((r, i) => (r.sequence = i));

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="1">
                <templates>
                    <t t-name="card">
                        <field name="id"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });

    expect(getKanbanRecordTexts(0)).toEqual(["4"]);
    expect(getKanbanRecordTexts(1)).toEqual(["1"]);

    // Drag the first kanban record on top of the last
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:last-child .o_kanban_record"
    );

    // load more twice to load all records of second column
    await clickKanbanLoadMore(1);
    await clickKanbanLoadMore(1);

    // Check records of the second column
    expect(getKanbanRecordTexts(1)).toEqual(["4", "1", "2", "3"]);
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
        "web_search_read",
        "web_search_read",
        "get_views",
        "onchange",
        "web_save",
        "web_read",
        "read_progress_bar",
        "web_read_group",
        "onchange",
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
        "web_search_read",
        "web_search_read",
        "web_read_group",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "get_views",
        "onchange",
        "web_save",
        "web_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "onchange",
        "web_save",
        "web_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "onchange",
    ]);
});

test.tags("desktop");
test("quickcreate in first column after moving a record from it", async () => {
    onRpc("/web/dataset/resequence", () => {
        return true;
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
test("grouped kanban: clear groupby when reloading", async () => {
    // in this test, we simulate that clearing the domain is slow, so that
    // clearing the groupby does not corrupt the data handled while
    // reloading the kanban view.
    const def = new Deferred();
    onRpc("web_read_group", async function ({ kwargs, parent }) {
        const result = parent();
        if (kwargs.domain.length === 0 && kwargs.groupby && kwargs.groupby[0] === "bar") {
            await def; // delay 1st update
        }
        return result;
    });

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
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[['foo', '=', 'norecord']]"/>
                <filter name="group_by_bar" domain="[]" string="GroupBy Bar" context="{ 'group_by': 'bar' }"/>
            </search>`,
        context: {
            search_default_group_by_bar: 1,
            search_default_my_filter: 1,
        },
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_renderer").not.toHaveClass("o_kanban_ungrouped");
    expect(queryAllTexts(".o_facet_value")).toEqual(["My Filter", "GroupBy Bar"]);

    await contains(".o_facet_remove:first").click();
    await contains(".o_facet_remove:only").click();
    def.resolve(); // simulate slow 1st update of kanban view
    await animationFrame();

    expect(".o_kanban_renderer").not.toHaveClass("o_kanban_grouped");
    expect(".o_kanban_renderer").toHaveClass("o_kanban_ungrouped");
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

test("keynav: right/left", async () => {
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
    });

    await pointerDown(getKanbanRecord({ index: 0 }));
    expect(getKanbanRecord({ index: 0 })).toBeFocused();

    await press("ArrowRight");
    expect(getKanbanRecord({ index: 1 })).toBeFocused();

    await press("ArrowLeft");
    expect(getKanbanRecord({ index: 0 })).toBeFocused();
});

test("keynav: down, with focus is inside a card", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <a href="#" class="o-this-is-focussable">ho! this is focussable</a>
                    </t>
                </templates>
            </kanban>`,
    });

    await pointerDown(getKanbanRecord({ index: 0 }).querySelector(".o-this-is-focussable"));
    await press("ArrowDown");

    expect(getKanbanRecord({ index: 1 })).toBeFocused();
});

test.tags("desktop");
test("keynav: grouped kanban", async () => {
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
    const cardsByColumn = queryAll(".o_kanban_group").map((root) =>
        queryAll(".o_kanban_record", { root })
    );
    const firstColumnFirstCard = cardsByColumn[0][0];
    const secondColumnFirstCard = cardsByColumn[1][0];
    const secondColumnSecondCard = cardsByColumn[1][1];

    // DOWN should focus the first card
    await press("ArrowDown");
    expect(firstColumnFirstCard).toBeFocused({
        message: "LEFT should select the first card of the first column",
    });

    // RIGHT should select the next column
    await press("ArrowRight");
    expect(secondColumnFirstCard).toBeFocused({
        message: "RIGHT should select the first card of the next column",
    });

    // DOWN should move up one card
    await press("ArrowDown");
    expect(secondColumnSecondCard).toBeFocused({
        message: "DOWN should select the second card of the current column",
    });

    // LEFT should go back to the first column
    await press("ArrowLeft");
    expect(firstColumnFirstCard).toBeFocused({
        message: "LEFT should select the first card of the first column",
    });
});

test.tags("desktop");
test("keynav: grouped kanban with empty columns", async () => {
    Partner._records[1].state = "abc";

    onRpc("web_read_group", function ({ parent }) {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        const result = parent();
        // add 2 empty columns in the middle
        result.groups.splice(1, 0, {
            state_count: 0,
            state: "md1",
            __domain: [["state", "=", "md1"]],
        });
        result.groups.splice(1, 0, {
            state_count: 0,
            state: "md2",
            __domain: [["state", "=", "md2"]],
        });
        // add 1 empty column in the beginning and the end
        result.groups.unshift({
            state_count: 0,
            state: "beg",
            __domain: [["state", "=", "beg"]],
        });
        result.groups.push({
            state_count: 0,
            state: "end",
            __domain: [["state", "=", "end"]],
        });
        return result;
    });

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
        groupBy: ["state"],
    });

    /**
     * Added columns in mockRPC are empty
     *
     *    | BEG | ABC  | MD1 | MD2 | GHI  | END
     *    |-----|------|-----|-----|------|-----
     *    |     | yop  |     |     | gnap |
     *    |     | blip |     |     | blip |
     */
    const cardsByColumn = queryAll(".o_kanban_group").map((root) =>
        queryAll(".o_kanban_record", { root })
    );
    const yop = cardsByColumn[1][0];
    const gnap = cardsByColumn[4][0];

    // DOWN should focus yop (first card)
    await press("ArrowDown");
    expect(yop).toBeFocused({
        message: "LEFT should select the first card of the first column that has a card",
    });

    // RIGHT should select the next column that has a card
    await press("ArrowRight");
    expect(gnap).toBeFocused({
        message: "RIGHT should select the first card of the next column that has a card",
    });

    // LEFT should go back to the first column that has a card
    await press("ArrowLeft");
    expect(yop).toBeFocused({
        message: "LEFT should select the first card of the first column that has a card",
    });
});

test.tags("desktop");
test("keynav: no global_click, press ENTER on card with a link", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban can_open="0">
                <templates>
                    <t t-name="card">
                        <a type="archive">Archive</a>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect.step("select record");
        },
    });

    await press("ArrowDown");
    expect(".o_kanban_record:first").toBeFocused();
    await press("Enter");

    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog main").toHaveText("Are you sure that you want to archive this record?");
    expect.verifySteps([]); // should not try to open the record
});

test.tags("desktop");
test("keynav: kanban with global_click", async () => {
    expect.assertions(2);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <a name="action_test" type="object" />
                    </t>
                </templates>
            </kanban>`,
        selectRecord(recordId) {
            expect(recordId).toBe(1, {
                message: "should call its selectRecord prop with the selected record",
            });
        },
    });

    await press("ArrowDown");
    expect(".o_kanban_record:first").toBeFocused();
    await press("Enter");
});

test.tags("desktop");
test(`kanban should ask to scroll to top on page changes`, async () => {
    // add records to be able to scroll
    for (let i = 5; i < 200; i++) {
        Partner._records.push({ id: i, foo: "foo" });
    }
    patchWithCleanup(KanbanController.prototype, {
        onPageChangeScroll() {
            super.onPageChangeScroll(...arguments);
            expect.step("scroll");
        },
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });
    // switch pages (should ask to scroll)
    await pagerNext();
    await pagerPrevious();
    // should ask to scroll when switching pages
    expect.verifySteps(["scroll", "scroll"]);

    // change the limit (should not ask to scroll)
    await contains(`.o_pager_value`).click();
    await contains(`.o_pager_value`).edit("1-100");
    await animationFrame();
    expect(getPagerValue()).toEqual([1, 100]);
    // should not ask to scroll when changing the limit
    expect.verifySteps([]);

    await contains(".o_content").scroll({ top: 250 });
    expect(".o_content").toHaveProperty("scrollTop", 250);

    // switch pages again (should still ask to scroll)
    await pagerNext();
    // this is still working after a limit change
    expect.verifySteps(["scroll"]);
    // Should effectively reset the scroll position
    expect(".o_content").toHaveProperty("scrollTop", 0);
});

test.tags("mobile");
test(`kanban should ask to scroll to top on page changes (mobile)`, async () => {
    // add records to be able to scroll
    for (let i = 5; i < 200; i++) {
        Partner._records.push({ id: i, foo: "foo" });
    }
    patchWithCleanup(KanbanController.prototype, {
        onPageChangeScroll() {
            super.onPageChangeScroll(...arguments);
            expect.step("scroll");
        },
    });

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });
    // switch pages (should ask to scroll)
    await pagerNext();
    await pagerPrevious();
    // should ask to scroll when switching pages
    expect.verifySteps(["scroll", "scroll"]);

    await contains(".o_kanban_view").scroll({ top: 250 });
    expect(".o_kanban_view").toHaveProperty("scrollTop", 250);

    // switch pages again (should still ask to scroll)
    await pagerNext();
    expect.verifySteps(["scroll"]);
    // Should effectively reset the scroll position
    expect(".o_kanban_view").toHaveProperty("scrollTop", 0);
});

test.tags("desktop");
test("set cover image", async () => {
    expect.assertions(9);

    IrAttachment._records = [
        {
            id: 1,
            name: "1.png",
            mimetype: "image/png",
            res_model: "partner",
            res_id: 1,
        },
        {
            id: 2,
            name: "2.png",
            mimetype: "image/png",
            res_model: "partner",
            res_id: 2,
        },
    ];
    Partner._fields.displayed_image_id = fields.Many2one({
        string: "Cover",
        relation: "ir.attachment",
    });

    onRpc("partner", "web_save", ({ args }) => {
        expect.step(args[0][0]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="displayed_image_id" widget="attachment_image"/>
                    </t>
                </templates>
            </kanban>`,
    });

    mockService("action", {
        switchView(_viewType, { mode, resModel, res_id, view_type }) {
            expect({ mode, resModel, res_id, view_type }).toBe({
                mode: "readonly",
                resModel: "partner",
                res_id: 1,
                view_type: "form",
            });
        },
    });

    await toggleKanbanRecordDropdown(0);
    await contains(".oe_kanban_action", {
        root: getDropdownMenu(getKanbanRecord({ index: 0 })),
    }).click();

    expect(queryAll("img", { root: getKanbanRecord({ index: 0 }) })).toHaveCount(0, {
        message: "Initially there is no image.",
    });

    await contains(".modal .o_kanban_cover_image img").click();
    await contains(".modal .btn-primary:first-child").click();

    expect('img[data-src*="/web/image/1"]').toHaveCount(1);

    await toggleKanbanRecordDropdown(1);
    const coverButton = getDropdownMenu(getKanbanRecord({ index: 1 })).querySelector("a");
    expect(queryText(coverButton)).toBe("Set Cover Image");
    await contains(coverButton).click();

    expect(".modal .o_kanban_cover_image").toHaveCount(1);
    expect(".modal .btn:contains(Select)").toHaveCount(1);
    expect(".modal .btn:contains(Discard)").toHaveCount(1);
    expect(".modal .btn:contains(Remove Cover Image)").toHaveCount(0);

    await dblclick(".modal .o_kanban_cover_image img"); // doesn't work
    await animationFrame();

    expect('img[data-src*="/web/image/2"]').toHaveCount(1);

    await contains(".o_kanban_record:first-child .o_attachment_image").click(); //Not sure, to discuss

    // should writes on both kanban records
    expect.verifySteps([1, 2]);
});

test.tags("desktop");
test("open file explorer if no cover image", async () => {
    expect.assertions(2);

    Partner._fields.displayed_image_id = fields.Many2one({
        string: "Cover",
        relation: "ir.attachment",
    });

    const uploadedPromise = new Deferred();
    await createFileInput({
        mockPost: async (route) => {
            if (route === "/web/binary/upload_attachment") {
                await uploadedPromise;
            }
            return "[]";
        },
        props: {},
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="displayed_image_id" widget="attachment_image"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);
    await contains(".oe_kanban_action", {
        root: getDropdownMenu(getKanbanRecord({ index: 0 })),
    }).click();
    await setInputFiles([]);
    await animationFrame();

    expect(`.o_file_input input`).not.toBeEnabled({
        message: "the upload button should be disabled on upload",
    });
    uploadedPromise.resolve();
    await animationFrame();

    expect(`.o_file_input input`).toBeEnabled({
        message: "the upload button should be enabled for upload",
    });
});

test.tags("desktop");
test("unset cover image", async () => {
    IrAttachment._records = [
        {
            id: 1,
            name: "1.png",
            mimetype: "image/png",
            res_model: "partner",
            res_id: 1,
        },
        {
            id: 2,
            name: "2.png",
            mimetype: "image/png",
            res_model: "partner",
            res_id: 2,
        },
    ];
    Partner._fields.displayed_image_id = fields.Many2one({
        string: "Cover",
        relation: "ir.attachment",
    });
    Partner._records[0].displayed_image_id = 1;
    Partner._records[1].displayed_image_id = 2;

    onRpc("partner", "web_save", ({ args }) => {
        expect.step(args[0][0]);
        expect(args[1].displayed_image_id).toBe(false);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="displayed_image_id" widget="attachment_image"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);
    await contains(".oe_kanban_action", {
        root: getDropdownMenu(getKanbanRecord({ index: 0 })),
    }).click();

    expect(
        queryAll('img[data-src*="/web/image/1"]', { root: getKanbanRecord({ index: 0 }) })
    ).toHaveCount(1);
    expect(
        queryAll('img[data-src*="/web/image/2"]', { root: getKanbanRecord({ index: 1 }) })
    ).toHaveCount(1);

    expect(".modal .o_kanban_cover_image").toHaveCount(1);
    expect(".modal .btn:contains(Select)").toHaveCount(1);
    expect(".modal .btn:contains(Discard)").toHaveCount(1);
    expect(".modal .btn:contains(Remove Cover Image)").toHaveCount(1);

    await contains(".modal .btn-secondary").click(); // click on "Remove Cover Image" button

    expect(queryAll("img", { root: getKanbanRecord({ index: 0 }) })).toHaveCount(0, {
        message: "The cover image should be removed.",
    });

    await toggleKanbanRecordDropdown(1);
    const coverButton = getDropdownMenu(getKanbanRecord({ index: 1 })).querySelector("a");
    expect(queryText(coverButton)).toBe("Set Cover Image");
    await contains(coverButton).click();

    await dblclick(".modal .o_kanban_cover_image img"); // doesn't work
    await animationFrame();

    expect(queryAll("img", { root: getKanbanRecord({ index: 1 }) })).toHaveCount(0, {
        message: "The cover image should be removed.",
    });
    // should writes on both kanban records
    expect.verifySteps([1, 2]);
});

test.tags("desktop");
test("ungrouped kanban with handle field", async () => {
    expect.assertions(3);

    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        expect(params.ids).toEqual([2, 1, 3, 4], {
            message: "should write the sequence in correct order",
        });
        return true;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="int_field" widget="handle" />
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual(["blip", "blip", "yop", "gnap"]);

    await contains(".o_kanban_record").dragAndDrop(queryFirst(".o_kanban_record:nth-child(4)"));

    expect(getKanbanRecordTexts()).toEqual(["blip", "yop", "gnap", "blip"]);
});

test("ungrouped kanban without handle field", async () => {
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return true;
    });

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
    });

    expect(getKanbanRecordTexts()).toEqual(["yop", "blip", "gnap", "blip"]);

    await contains(".o_kanban_record").dragAndDrop(queryFirst(".o_kanban_record:nth-child(4)"));

    expect(getKanbanRecordTexts()).toEqual(["yop", "blip", "gnap", "blip"]);
    expect.verifySteps([]);
});

test("click on image field in kanban (with default global_click)", async () => {
    expect.assertions(2);

    Partner._fields.image = fields.Binary();
    Partner._records[0].image = "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="image" widget="image"/>
                    </t>
                </templates>
            </kanban>`,
        selectRecord(recordId) {
            expect(recordId).toBe(1, {
                message: "should call its selectRecord prop with the clicked record",
            });
        },
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    await contains(".o_field_image").click();
});

test("kanban view with boolean field", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="bar"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record input:disabled").toHaveCount(4);
    expect(".o_kanban_record input:checked").toHaveCount(3);
    expect(".o_kanban_record input:not(:checked)").toHaveCount(1);
});

test("kanban view with boolean widget", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="bar" widget="boolean"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(
        queryAll("div.o_field_boolean .o-checkbox", { root: getKanbanRecord({ index: 0 }) })
    ).toHaveCount(1);
});

test("kanban view with boolean toggle widget", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="bar" widget="boolean_toggle"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(getKanbanRecord({ index: 0 }).querySelector("[name='bar'] input")).toBeChecked();
    expect(getKanbanRecord({ index: 1 }).querySelector("[name='bar'] input")).toBeChecked();

    await click("[name='bar'] input:only", { root: getKanbanRecord({ index: 1 }) });
    await animationFrame();

    expect(getKanbanRecord({ index: 0 }).querySelector("[name='bar'] input")).toBeChecked();
    expect(getKanbanRecord({ index: 1 }).querySelector("[name='bar'] input")).not.toBeChecked();
});

test("kanban view with monetary and currency fields without widget", async () => {
    const mockedCurrencies = {};
    for (const record of Currency._records) {
        mockedCurrencies[record.id] = record;
    }
    patchWithCleanup(currencies, mockedCurrencies);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="currency_id"/>
                <templates>
                    <t t-name="card">
                        <field name="salary"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual([
        `$ 1,750.00`,
        `$ 1,500.00`,
        `2,000.00 €`,
        `$ 2,222.00`,
    ]);
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
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "read_progress_bar",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "web_search_read",
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
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "read_progress_bar",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_search_read",
        "web_search_read",
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
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "read_progress_bar",
        "web_save",
        "read_progress_bar",
        "/web/dataset/resequence",
        "read",
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
        "web_search_read",
        "web_search_read",
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
    expect.verifySteps([
        "web_save",
        "read_progress_bar",
        "web_search_read",
        "/web/dataset/resequence",
        "read",
    ]);
});

test("kanban widget can extract props from attrs", async () => {
    class TestWidget extends Component {
        static template = xml`<div class="o-test-widget-option" t-esc="props.title"/>`;
        static props = ["*"];
    }
    const testWidget = {
        component: TestWidget,
        extractProps: ({ attrs }) => {
            return {
                title: attrs.title,
            };
        },
    };
    viewWidgetRegistry.add("widget_test_option", testWidget);
    after(() => viewWidgetRegistry.remove("widget_test_option"));

    await mountView({
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <widget name="widget_test_option" title="Widget with Option"/>
                    </t>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
    });

    expect(".o-test-widget-option").toHaveCount(4);
    expect(".o-test-widget-option:first").toHaveText("Widget with Option");
});

test("action/type attributes on kanban arch, type='object'", async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(`doActionButton type ${params.type} name ${params.name}`);
            params.onClose();
        },
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban action="a1" type="object">
                <templates>
                    <t t-name="card">
                        <p>some value</p><field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);
    await contains(".o_kanban_record p").click();
    expect.verifySteps(["doActionButton type object name a1", "web_search_read"]);
});

test("action/type attributes on kanban arch, type='action'", async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(`doActionButton type ${params.type} name ${params.name}`);
            params.onClose();
        },
    });

    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban action="a1" type="action">
                <templates>
                    <t t-name="card">
                        <p>some value</p><field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);
    await contains(".o_kanban_record p").click();
    expect.verifySteps(["doActionButton type action name a1", "web_search_read"]);
});

test("Missing t-key is automatically filled with a warning", async () => {
    patchWithCleanup(console, { warn: () => expect.step("warning") });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div>
                            <span t-foreach="[1, 2, 3]" t-as="i" t-esc="i" />
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect.verifySteps(["warning"]);
    expect(getKanbanRecord({ index: 0 })).toHaveText("123");
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

test("Allow use of 'editable'/'deletable' in ungrouped kanban", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="card">
                        <button t-if="widget.editable">EDIT</button>
                        <button t-if="widget.deletable">DELETE</button>
                    </div>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecordTexts()).toEqual([
        "EDITDELETE",
        "EDITDELETE",
        "EDITDELETE",
        "EDITDELETE",
    ]);
});

test.tags("desktop");
test("folded groups kept when leaving/coming back", async () => {
    Partner._views = {
        "kanban,false": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        "search,false": "<search/>",
        "form,false": "<form/>",
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
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_column_folded").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(4);

    // fold the first group
    const clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Fold");
    expect(".o_column_folded").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(2);

    // open a record and go back
    await contains(".o_kanban_record").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".breadcrumb-item a").click();
    expect(".o_column_folded").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(2);
});

test.tags("desktop");
test("filter groups kept when leaving/coming back", async () => {
    Partner._records[1].state = "abc";
    Partner._views = {
        "kanban,false": `
            <kanban>
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <t t-name="card">
                        <field name="id" />
                    </t>
                </templates>
            </kanban>`,
        "search,false": "<search/>",
        "form,false": `
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

test.tags("desktop");
test("folded groups kept when leaving/coming back (grouped by date)", async () => {
    Partner._fields.date = fields.Date({ default: "2022-10-10" });
    Partner._records[0].date = "2022-05-10";
    Partner._views = {
        "kanban,false": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        "search,false": "<search/>",
        "form,false": "<form/>",
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
            group_by: ["date"],
        },
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_column_folded").toHaveCount(0);
    expect(".o_kanban_record").toHaveCount(4);

    // fold the second column
    const clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Fold");
    expect(".o_column_folded").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(1);

    // open a record and go back
    await contains(".o_kanban_record").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".breadcrumb-item a").click();
    expect(".o_column_folded").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(1);
});

test.tags("desktop");
test("loaded records kept when leaving/coming back", async () => {
    Partner._views = {
        "kanban,false": `
            <kanban limit="1">
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        "search,false": "<search/>",
        "form,false": "<form/>",
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
            group_by: ["product_id"],
        },
    });

    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_record").toHaveCount(2);

    // load more records in second group
    await clickKanbanLoadMore(1);
    expect(".o_kanban_record").toHaveCount(3);

    // open a record and go back
    await contains(".o_kanban_record").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".breadcrumb-item a").click();
    expect(".o_kanban_record").toHaveCount(3);
});

test("basic rendering with 2 groupbys", async () => {
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar", "product_id"],
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test("basic rendering with a date groupby with a granularity", async () => {
    Partner._records[0].date = "2022-06-23";

    stepAllNetworkCalls();
    onRpc("web_read_group", ({ method, kwargs }) => {
        expect(kwargs.fields).toEqual([]);
        expect(kwargs.groupby).toEqual(["date:day"]);
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["date:day"],
    });

    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
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
        createRecord: () => {
            expect.step("create record");
        },
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

    expect.verifySteps([]);

    await createKanbanRecord();

    expect.verifySteps(["create record"]);
    expect(".o_kanban_quick_create").toHaveCount(0);
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
        createRecord: () => {
            expect.step("create record");
        },
    });

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "ABC");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("ABC");

    await contains(".o_control_panel").click();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("ABC");

    await quickCreateKanbanRecord(1);

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("");

    await editKanbanRecordQuickCreateInput("display_name", "ABC");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("ABC");

    await contains(".o_kanban_load_more button").click();

    expect(".o_kanban_quick_create").toHaveCount(0);

    await quickCreateKanbanRecord();

    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_quick_create").toHaveCount(1);

    await editKanbanRecordQuickCreateInput("display_name", "ABC");

    expect(".o_kanban_quick_create [name=display_name] input").toHaveValue("ABC");
    expect.verifySteps([]);

    await createKanbanRecord();

    expect.verifySteps(["create record"]);
    expect(".o_kanban_quick_create").toHaveCount(0);
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

test("dropdown is closed on item click", async () => {
    Partner._records.splice(1, 3); // keep one record only

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="menu">
                        <a role="menuitem" class="dropdown-item">Item</a>
                    </t>
                    <t t-name="card">
                        <div/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o-dropdown--menu").toHaveCount(0);

    await toggleKanbanRecordDropdown();

    expect(".o-dropdown--menu").toHaveCount(1);

    await contains(".o-dropdown--menu .dropdown-item").click();

    expect(".o-dropdown--menu").toHaveCount(0);
});

test("can use JSON in kanban template", async () => {
    Partner._records = [{ id: 1, foo: '["g", "e", "d"]' }];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <div>
                            <span t-foreach="JSON.parse(record.foo.raw_value)" t-as="v" t-key="v_index" t-esc="v"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span").toHaveCount(3);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveText("ged");
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
        "web_search_read",
        "web_search_read",
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
        "web_search_read",
        "web_search_read",
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
            <kanban on_create="quick_create">
                <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                <templates>
                    <div t-name="card">
                        <field name="state" widget="state_selection" />
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
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
test("keep focus in cp when pressing arrowdown and no kanban card", async () => {
    Partner._records = [];

    await mountView({
        type: "kanban",
        resModel: "partner",
        groupBy: ["product_id"],
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
    });

    // Check that there is a column quick create
    expect(".o_column_quick_create").toHaveCount(1);
    await editKanbanColumnName("new col");
    await validateKanbanColumn();

    // Check that there is only one group and no kanban card
    expect(".o_kanban_group").toHaveCount(1);
    expect(".o_kanban_group.o_kanban_no_records").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(0);

    // Check that the focus is on the searchview input
    await quickCreateKanbanRecord();
    expect(".o_kanban_group.o_kanban_no_records").toHaveCount(1);
    expect(".o_kanban_quick_create").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(0);

    // Somehow give the focus in the control panel, i.e. in the search view
    // Note that a simple click in the control panel should normally close the quick
    // create, so in order to give the focus in the search input, the user would
    // normally have to right-click on it then press escape. These are behaviors
    // handled through the browser, so we simply call focus directly here.
    queryFirst(".o_searchview_input").focus();

    // Make sure no async code will have a side effect on the focused element
    await animationFrame();
    expect(".o_searchview_input").toBeFocused();

    // Trigger the ArrowDown hotkey
    await press("ArrowDown");
    await animationFrame();
    expect(".o_searchview_input").toBeFocused();
});

test.tags("desktop");
test("no leak of TransactionInProgress (grouped case)", async () => {
    const def = new Deferred();
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return def;
    });

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
        groupBy: ["state"],
    });

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveText("yop");
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveText("blip");
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);

    expect.verifySteps([]);

    // move "yop" from first to second column
    await contains(".o_kanban_group:nth-child(1) .o_kanban_record").dragAndDrop(
        queryFirst(".o_kanban_group:nth-child(2)")
    );

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(queryAllTexts(".o_kanban_group:nth-child(2) .o_kanban_record")).toEqual(["blip", "yop"]);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);
    expect.verifySteps(["resequence"]);

    // try to move "yop" from second to third column
    await contains(".o_kanban_group:nth-child(2) .o_kanban_record:nth-child(3)").dragAndDrop(
        ".o_kanban_group:nth-child(3)"
    );

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
    expect(queryAllTexts(".o_kanban_group:nth-child(2) .o_kanban_record")).toEqual(["blip", "yop"]);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);
    expect.verifySteps([]);

    def.resolve();
    await animationFrame();

    // try again to move "yop" from second to third column
    await contains(".o_kanban_group:nth-child(2) .o_kanban_record:nth-child(3)").dragAndDrop(
        ".o_kanban_group:nth-child(3)"
    );

    expect(".o_kanban_group:nth-child(1) .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(3);
    expect(queryAllTexts(".o_kanban_group:nth-child(3) .o_kanban_record")).toEqual([
        "gnap",
        "blip",
        "yop",
    ]);
    expect.verifySteps(["resequence"]);
});

test.tags("desktop");
test("no leak of TransactionInProgress (not grouped case)", async () => {
    const def = new Deferred();
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return def;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban records_draggable="1">
                <field name="int_field" widget="handle" />
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "blip",
        "blip",
        "yop",
        "gnap",
    ]);
    expect.verifySteps([]);

    // move second "blip" to third place
    await contains(".o_kanban_record:nth-child(2)").dragAndDrop(".o_kanban_record:nth-child(3)");

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "blip",
        "yop",
        "blip",
        "gnap",
    ]);
    expect.verifySteps(["resequence"]);

    // try again
    await contains(".o_kanban_record:nth-child(2)").dragAndDrop(".o_kanban_record:nth-child(3)");
    expect.verifySteps([]);

    def.resolve();
    await animationFrame();

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "blip",
        "yop",
        "blip",
        "gnap",
    ]);

    await contains(".o_kanban_record:nth-child(3)").dragAndDrop(".o_kanban_record:nth-child(4)");

    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "blip",
        "yop",
        "gnap",
        "blip",
    ]);
    expect.verifySteps(["resequence"]);
});

test("fieldDependencies support for fields", async () => {
    const customField = {
        component: class CustomField extends Component {
            static template = xml`<span t-esc="props.record.data.int_field"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "int_field", type: "integer" }],
    };
    fieldRegistry.add("custom_field", customField);
    after(() => fieldRegistry.remove("custom_field"));

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="custom_field"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("[name=foo] span:first").toHaveText("10");
});

test("fieldDependencies support for fields: dependence on a relational field", async () => {
    const customField = {
        component: class CustomField extends Component {
            static template = xml`<span t-esc="props.record.data.product_id[1]"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "product_id", type: "many2one", relation: "product" }],
    };
    fieldRegistry.add("custom_field", customField);
    after(() => fieldRegistry.remove("custom_field"));

    stepAllNetworkCalls();

    await mountView({
        resModel: "partner",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="custom_field"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("[name=foo] span:first").toHaveText("hello");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);
});

test("column quick create - title and placeholder", async function (assert) {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_column_quick_create .o_quick_create_folded").toHaveText("Product");

    await contains("button.o_kanban_add_column").click();

    expect(
        ".o_column_quick_create .o_quick_create_unfolded .input-group .form-control"
    ).toHaveAttribute("placeholder", "Product...");
});

test.tags("desktop");
test("fold a column and drag record on it should not unfold it", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="id"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(1) })).toHaveCount(2);

    const clickColumnAction = await toggleKanbanColumnActions(1);
    clickColumnAction("Fold");
    await animationFrame();

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(getKanbanColumn(1)).toHaveText("xmo\n(2)");

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(".o_column_folded");

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(getKanbanColumn(1)).toHaveText("xmo\n(3)");
});

test.tags("desktop");
test("drag record on initially folded column should not unfold it", async () => {
    Product._records[1].fold = true;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="id"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(queryText(getKanbanColumn(1))).toBe("xmo\n(2)");

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(".o_column_folded");

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(1);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");
    expect(queryText(getKanbanColumn(1))).toBe("xmo\n(3)");
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
        "web_search_read",
        "web_search_read",
        "web_save",
        "read_progress_bar",
        "web_read_group",
    ]);
});

test.tags("desktop");
test("quick create record in grouped kanban in a form view dialog", async () => {
    Partner._fields.foo = fields.Char({ default: "ABC" });
    Partner._views["form,false"] = `<form><field name="bar"/></form>`;

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

    await clickModalButton({ text: "Save & Close" });

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
        "web_read_group", // initial read_group
        "web_search_read", // initial search_read (first column)
        "web_search_read", // initial search_read (second column)
        "onchange", // quick create
        "name_create", // should perform a name_create to create the record
        "get_views", // load views for form view dialog
        "onchange", // load of a virtual record in form view dialog
        "web_save", // save virtual record
        "web_read", // read the created record to get foo value
        "onchange", // reopen the quick create automatically
    ]);
});

test.tags("desktop");
test("no sample data when all groups are folded then one is unfolded", async () => {
    Product._records.forEach((group) => {
        group.fold = true;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="id"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_column_folded").toHaveCount(2);

    await contains(".o_kanban_group").click();

    expect(".o_column_folded").toHaveCount(1);
    expect(".o_kanban_record").toHaveCount(2);
    expect("o_view_sample_data").toHaveCount(0);
});

test.tags("desktop");
test("no content helper, all groups folded with (unloaded) records", async () => {
    Product._records.forEach((group) => {
        group.fold = true;
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="id"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_column_folded").toHaveCount(2);
    expect(queryAllTexts(".o_column_title")).toEqual(["hello\n(2)", "xmo\n(2)"]);
    expect(".o_nocontent_help").toHaveCount(0);
});

test.tags("desktop");
test("Move multiple records in different columns simultaneously", async () => {
    const def = new Deferred();
    onRpc("read", () => def);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["state"],
    });

    expect(getKanbanRecordTexts()).toEqual(["1", "2", "3", "4"]);

    // Move 3 at end of 1st column
    await contains(".o_kanban_group:last-of-type .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first"
    );

    expect(getKanbanRecordTexts()).toEqual(["1", "3", "2", "4"]);

    // Move 4 at end of 1st column
    await contains(".o_kanban_group:last-of-type .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first"
    );

    expect(getKanbanRecordTexts()).toEqual(["1", "3", "4", "2"]);

    def.resolve();
    await animationFrame();

    expect(getKanbanRecordTexts()).toEqual(["1", "3", "4", "2"]);
});

test.tags("desktop");
test("drag & drop: content scrolls when reaching the edges", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="card">
                        <field name="id" />
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["state"],
    });

    const width = 600;
    const content = queryOne(".o_content");
    content.setAttribute("style", `max-width:${width}px;overflow:auto;`);

    expect(content.scrollLeft).toBe(0);
    expect(content.getBoundingClientRect().width).toBe(600);
    expect(".o_kanban_record.o_dragged").toHaveCount(0);

    // Drag first record of first group to the right
    let dragActions = await contains(".o_kanban_record").drag();
    await dragActions.moveTo(".o_kanban_group:nth-child(3) .o_kanban_record:first");

    expect(".o_kanban_record.o_dragged").toHaveCount(1);

    // wait 30 frames, should be enough (default kanban speed is 20px per tick)
    await advanceFrame(30);

    // Should be at the end of the content
    expect(content.scrollLeft + width).toBe(content.scrollWidth);

    // Cancel drag: press "Escape"
    await press("Escape");
    await animationFrame();

    expect(".o_kanban_record.o_dragged").toHaveCount(0);

    // Drag first record of last group to the left
    dragActions = await contains(".o_kanban_group:nth-child(3) .o_kanban_record").drag();
    await dragActions.moveTo(".o_kanban_record:first");

    expect(".o_kanban_record.o_dragged").toHaveCount(1);

    await advanceFrame(30);

    expect(content.scrollLeft).toBe(0);

    // Cancel drag: click outside
    await contains(".o_kanban_renderer").focus();

    expect(".o_kanban_record.o_dragged").toHaveCount(0);
});

test("attribute default_order", async () => {
    class CustomModel extends models.Model {
        _name = "custom.model";

        int = fields.Integer();

        _records = [
            { id: 1, int: 1 },
            { id: 2, int: 3 },
            { id: 3, int: 2 },
        ];
    }
    defineModels([CustomModel]);

    await mountView({
        type: "kanban",
        resModel: "custom.model",
        arch: `
            <kanban default_order="int">
                <templates>
                    <div t-name="card">
                        <field name="int" />
                    </div>
                </templates>
            </kanban>`,
    });
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["1", "2", "3"]);
});

test.tags("desktop");
test("d&d records grouped by m2o with m2o displayed in records", async () => {
    const readIds = [[2], [1, 3, 2]];
    const def = new Deferred();
    onRpc("read", ({ method, args }) => {
        expect(args[0]).toEqual(readIds[1]);
        return def;
    });
    stepAllNetworkCalls();

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="product_id" widget="many2one"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
    ]);
    expect(queryAllTexts(".o_kanban_record")).toEqual(["hello", "hello", "xmo", "xmo"]);

    await contains(".o_kanban_group:nth-child(2) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:first-child"
    );
    expect(queryAllTexts(".o_kanban_record")).toEqual(["hello", "hello", "hello", "xmo"]);

    def.resolve();
    await animationFrame();

    expect.verifySteps(["web_save", "/web/dataset/resequence", "read"]);
    expect(queryAllTexts(".o_kanban_record")).toEqual(["hello", "hello", "hello", "xmo"]);
});

test("Can't use KanbanRecord implementation details in arch", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div>
                            <t t-esc="__owl__"/>
                            <t t-esc="props"/>
                            <t t-esc="env"/>
                            <t t-esc="render"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_kanban_record:first").toHaveInnerHTML("<div></div>");
});

test.tags("desktop");
test("rerenders only once after resequencing records", async () => {
    // Actually it's not once, because we must render directly after the drag&drop s.t. the dropped
    // record remains where it has been dropped, once again after saving/reloading the record as
    // we rebuild record.data, and finally after the call to resequence, to re-enable the resequence
    // feature on the record (canResequence props).
    let saveDef = new Deferred();
    let resequenceDef = new Deferred();
    const renderCounts = {};
    patchWithCleanup(KanbanRecord.prototype, {
        setup() {
            super.setup();
            onWillRender(() => {
                const id = this.props.record.resId;
                renderCounts[id] = renderCounts[id] || 0;
                renderCounts[id]++;
            });
        },
    });

    onRpc("web_save", () => saveDef);
    onRpc("/web/dataset/resequence", () => resequenceDef);
    stepAllNetworkCalls();

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
    });

    expect(renderCounts).toEqual({ 1: 1, 2: 1, 3: 1, 4: 1 });

    // drag yop to the second column
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(renderCounts).toEqual({ 1: 3, 2: 1, 3: 1, 4: 1 });

    saveDef.resolve();
    await animationFrame();

    expect(renderCounts).toEqual({ 1: 4, 2: 1, 3: 1, 4: 1 });

    resequenceDef.resolve();
    await animationFrame();

    expect(renderCounts).toEqual({ 1: 5, 2: 1, 3: 1, 4: 1 });

    // drag gnap to the second column
    saveDef = new Deferred();
    resequenceDef = new Deferred();
    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(renderCounts).toEqual({ 1: 5, 2: 1, 3: 2, 4: 1 });

    saveDef.resolve();
    await animationFrame();

    expect(renderCounts).toEqual({ 1: 5, 2: 1, 3: 3, 4: 1 });

    resequenceDef.resolve();
    await animationFrame();

    expect(renderCounts).toEqual({ 1: 5, 2: 1, 3: 4, 4: 1 });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "web_search_read",
        "web_search_read",
        "web_save",
        "/web/dataset/resequence",
        "read",
        "web_save",
        "/web/dataset/resequence",
        "read",
    ]);
});

test("sample server: _mockWebReadGroup API", async () => {
    Partner._records = [];

    patchWithCleanup(SampleServer.prototype, {
        async _mockWebReadGroup() {
            const result = await super._mockWebReadGroup(...arguments);
            const { "date:month": dateValue } = result.groups[0];
            expect(dateValue).toBe("December 2022");
            return result;
        },
    });

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    date_count: 0,
                    state: false,
                    "date:month": "December 2022",
                    __range: {
                        "date:month": {
                            from: "2022-12-01",
                            to: "2023-01-01",
                        },
                    },
                    __domain: [
                        ["date", ">=", "2022-12-01"],
                        ["date", "<", "2023-01-01"],
                    ],
                },
            ],
            length: 1,
        };
    });

    await mountView({
        arch: `
            <kanban sample="1">
                <templates>
                    <div t-name="card">
                        <field name="display_name"/>
                    </div>
                </templates>
            </kanban>`,
        groupBy: ["date:month"],
        resModel: "partner",
        type: "kanban",
        noContentHelp: "No content helper",
    });

    expect(".o_kanban_view .o_view_sample_data").toHaveCount(1);
    expect(".o_kanban_group").toHaveCount(1);
    expect(".o_kanban_group .o_column_title").toHaveText("December 2022");
    expect(".o_kanban_group .o_kanban_record").toHaveCount(16);
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

    expect.verifySteps(["get_views", "read_progress_bar", "web_read_group", "web_search_read"]);
    queryOne(".o_content").scrollTo = (params) => {
        expect.step("scrolled");
        expect(params.top).toBe(0);
    };

    await contains(getKanbanProgressBars(0)[0]).click();

    expect.verifySteps([
        "web_read_group",
        "web_search_read",
        "read_progress_bar",
        "web_read_group",
        "web_read_group",
        "scrolled",
    ]);
    expect(getKanbanColumn(1)).toHaveClass("o_column_folded");

    await contains(getKanbanColumn(1)).click();

    expect.verifySteps(["web_search_read", "scrolled"]);
});

test.tags("desktop");
test(`kanban view: press "hotkey" to execute header button action`, async () => {
    mockService("action", {
        doActionButton(params) {
            const { name } = params;
            expect.step(`execute_action: ${name}`);
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
                <header>
                    <button name="display" type="object" class="display" string="display" display="always" data-hotkey="a"/>
                </header>
                <field name="bar" />
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
    });

    await press(["alt", "a"]);
    await tick();
    expect.verifySteps(["execute_action: display"]);
});

test.tags("desktop");
test("action button in controlPanel with display='always'", async () => {
    const domain = [["id", "=", 1]];

    mockService("action", {
        async doActionButton(params) {
            const { buttonContext, context, name, resModel, resIds, type } = params;
            expect.step("execute_action");
            // Action's own properties
            expect(name).toBe("display");
            expect(type).toBe("object");

            // The action's execution context
            expect(buttonContext).toEqual({
                active_domain: domain,
                active_ids: [],
                active_model: "partner",
            });

            expect(context).toEqual({
                a: true,
                allowed_company_ids: [1],
                lang: "en",
                tz: "taht",
                uid: 7,
            });
            expect(resModel).toBe("partner");
            expect(resIds).toEqual([]);
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
                <header>
                    <button name="display" type="object" class="display" string="display" display="always"/>
                    <button name="display" type="object" class="display_invisible" string="invisible 1" display="always" invisible="1"/>
                    <button name="display" type="object" class="display_invisible_2" string="invisible context" display="always" invisible="context.get('a')"/>
                    <button name="default-selection" type="object" class="default-selection" string="default-selection"/>
                </header>
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        domain,
        context: {
            a: true,
        },
    });

    const cpButtons = queryAll(".o_control_panel_main_buttons button:visible");
    expect(queryAllTexts(cpButtons)).toEqual(["New", "display"]);
    expect(cpButtons[1]).toHaveClass("display");

    await contains(cpButtons[1]).click();

    expect.verifySteps(["execute_action"]);
});

test.tags("desktop");
test("Keep scrollTop when loading records with load more", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div style="height:1000px;"><field name="id"/></div>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
        limit: 1,
    });
    queryOne(".o_kanban_renderer").style.overflow = "scroll";
    queryOne(".o_kanban_renderer").style.height = "500px";
    const clickKanbanLoadMoreButton = queryFirst(".o_kanban_load_more button");
    clickKanbanLoadMoreButton.scrollIntoView();
    const previousScrollTop = queryOne(".o_kanban_renderer").scrollTop;
    await contains(clickKanbanLoadMoreButton).click();
    expect(previousScrollTop).not.toBe(0, { message: "Should not have the scrollTop value at 0" });
    expect(queryOne(".o_kanban_renderer").scrollTop).toBe(previousScrollTop);
});

test("Kanban: no reset of the groupby when a non-empty column is deleted", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban default_group_by="product_id">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search>
                <filter name="groupby_category" string="Category" context="{'group_by': 'category_ids'}"/>
            </search>`,
    });

    // validate presence of the search arch info
    await toggleSearchBarMenu();
    expect(".o_group_by_menu span.o_menu_item").toHaveCount(1);

    // select the groupby:category_ids filter
    await contains(".o_group_by_menu span.o_menu_item").click();
    // check the initial rendering
    expect(".o_kanban_group").toHaveCount(3, { message: "should have three columns" });

    // check availability of delete action in kanban header's config dropdown
    await toggleKanbanColumnActions(2);
    expect(queryAll(".o_column_delete", { root: getKanbanColumnDropdownMenu(2) })).toHaveCount(1, {
        message: "should be able to delete the column",
    });

    // delete second column (first cancel the confirm request, then confirm)
    let clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Delete");
    await contains(".o_dialog footer .btn-secondary").click();

    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("gold\n(1)");

    clickColumnAction = await toggleKanbanColumnActions(1);
    await clickColumnAction("Delete");
    await contains(".o_dialog footer .btn-primary").click();

    expect(".o_kanban_group").toHaveCount(2, { message: "should now have two columns" });
    expect(queryText(".o_column_title", { root: getKanbanColumn(1) })).toBe("silver\n(1)");
    expect(queryText(".o_column_title", { root: getKanbanColumn(0) })).toBe("None\n(3)");
});

test.tags("desktop");
test("searchbar filters are displayed directly", async () => {
    let def;
    onRpc("web_search_read", () => def);

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
        searchViewArch: `
            <search>
                <filter name="some_filter" string="Some Filter" domain="[['foo', '!=', 'bar']]"/>
            </search>`,
    });

    expect(getFacetTexts()).toEqual([]);

    // toggle a filter, and slow down the web_search_read rpc
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");
    expect(getFacetTexts()).toEqual(["Some Filter"]);

    def.resolve();
    await animationFrame();
    expect(getFacetTexts()).toEqual(["Some Filter"]);
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

test.tags("desktop");
test("group by properties and drag and drop", async () => {
    expect.assertions(7);

    Partner._fields.properties = fields.Properties({
        definition_record: "parent_id",
        definition_record_field: "properties_definition",
    });
    Partner._fields.parent_id = fields.Many2one({ relation: "partner" });
    Partner._fields.properties_definition = fields.PropertiesDefinition();

    Partner._records[0].properties_definition = [
        {
            name: "my_char",
            string: "My Char",
            type: "char",
        },
    ];
    Partner._records[1].parent_id = 1;
    Partner._records[1].properties = [
        {
            name: "my_char",
            string: "My Char",
            type: "char",
            value: "aaa",
        },
    ];
    Partner._records[2].parent_id = 1;
    Partner._records[2].properties = [
        {
            name: "my_char",
            string: "My Char",
            type: "char",
            value: "bbb",
        },
    ];
    Partner._records[3].parent_id = 2;

    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    "properties.my_char": false,
                    __domain: [["properties.my_char", "=", false]],
                    "properties.my_char_count": 2,
                },
                {
                    "properties.my_char": "aaa",
                    __domain: [["properties.my_char", "=", "aaa"]],
                    "properties.my_char_count": 1,
                },
                {
                    "properties.my_char": "bbb",
                    __domain: [["properties.my_char", "=", "bbb"]],
                    "properties.my_char_count": 1,
                },
            ],
            length: 3,
        };
    });
    onRpc("web_search_read", ({ kwargs }) => {
        const value = kwargs.domain[0][2];
        return {
            length: 1,
            records: [
                {
                    id: value === "aaa" ? 2 : 3,
                    properties: [
                        {
                            name: "my_char",
                            string: "My Char",
                            type: "char",
                            value: value,
                        },
                    ],
                },
            ],
        };
    });
    onRpc("/web/dataset/resequence", () => {
        expect.step("resequence");
        return true;
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const expected = {
            properties: [
                {
                    name: "my_char",
                    string: "My Char",
                    type: "char",
                    value: "bbb",
                },
            ],
        };
        expect(args[1]).toEqual(expected);
    });
    onRpc("get_property_definition", ({ args }) => {
        expect.step("get_property_definition");
        return {
            name: "my_char",
            type: "char",
        };
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="properties"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["properties.my_char"],
    });

    expect.verifySteps(["get_property_definition"]);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(1);

    await contains(".o_kanban_group:nth-child(2) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(3)"
    );

    expect.verifySteps(["web_save", "resequence"]);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(0);
    expect(".o_kanban_group:nth-child(3) .o_kanban_record").toHaveCount(2);
});

test("kanbans with basic and custom compiler, same arch", async () => {
    // In this test, the exact same arch will be rendered by 2 different kanban renderers:
    // once with the basic one, and once with a custom renderer having a custom compiler. The
    // purpose of the test is to ensure that the template is compiled twice, once by each
    // compiler, even though the arch is the same.
    class MyKanbanCompiler extends KanbanCompiler {
        setup() {
            super.setup();
            this.compilers.push({ selector: "div", fn: this.compileDiv });
        }

        compileDiv(node, params) {
            const compiledNode = this.compileGenericNode(node, params);
            compiledNode.setAttribute("class", "my_kanban_compiler");
            return compiledNode;
        }
    }
    class MyKanbanRecord extends KanbanRecord {}
    MyKanbanRecord.Compiler = MyKanbanCompiler;
    class MyKanbanRenderer extends KanbanRenderer {}
    MyKanbanRenderer.components = {
        ...KanbanRenderer.components,
        KanbanRecord: MyKanbanRecord,
    };
    viewRegistry.add("my_kanban", {
        ...kanbanView,
        Renderer: MyKanbanRenderer,
    });
    after(() => viewRegistry.remove("my_kanban"));

    Partner._fields.one2many = fields.One2many({ relation: "partner" });
    Partner._records[0].one2many = [1];
    Partner._views["form,false"] = `<form><field name="one2many" mode="kanban"/></form>`;
    Partner._views["search,false"] = `<search/>`;
    Partner._views["kanban,false"] = `
        <kanban js_class="my_kanban">
            <templates>
                <t t-name="card">
                    <div><field name="foo"/></div>
                </t>
            </templates>
        </kanban>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
    });

    // main kanban, custom view
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_my_kanban_view").toHaveCount(1);
    expect(".my_kanban_compiler").toHaveCount(4);

    // switch to form
    await contains(".o_kanban_record").click();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_field_widget[name=one2many]").toHaveCount(1);

    // x2many kanban, basic renderer
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".my_kanban_compiler").toHaveCount(0);
});

test("grouped on field with readonly expression depending on context", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="product_id" readonly="context.get('abc')" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
        context: { abc: true },
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);
});

test.tags("desktop");
test("grouped on field with readonly expression depending on fields", async () => {
    // Fields are not available in the current context as the drag and drop must be enabled globally
    // for the view, it's not a per record thing.
    // So if the readonly expression contains fields, it will resolve to readonly === false and
    // the drag and drop will be enabled.
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                        <field name="product_id" readonly="foo == 'yop'" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(2);

    await contains(".o_kanban_group:first-child .o_kanban_record").dragAndDrop(
        ".o_kanban_group:nth-child(2)"
    );

    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);
});

test.tags("desktop");
test("quick create a column by pressing enter when input is focused", async () => {
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
    });

    expect(".o_kanban_group").toHaveCount(2);

    await quickCreateKanbanColumn();

    // We don't use the editInput helper as it would trigger a change event automatically.
    // We need to wait for the enter key to trigger the event.
    await press("N");
    await press("e");
    await press("w");
    await press("Enter");
    await animationFrame();

    expect(".o_kanban_group").toHaveCount(3);
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

test.tags("desktop");
test("click on empty kanban must shake the NEW button", async () => {
    onRpc("web_read_group", () => {
        // override read_group to return empty groups, as this is
        // the case for several models (e.g. project.task grouped
        // by stage_id)
        return {
            groups: [
                {
                    __domain: [["product_id", "=", 3]],
                    product_id_count: 0,
                    product_id: [3, "xplone"],
                },
                {
                    __domain: [["product_id", "=", 5]],
                    product_id_count: 0,
                    product_id: [5, "xplan"],
                },
            ],
            length: 2,
        };
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

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be 2 columns" });
    expect(".o_kanban_record").toHaveCount(0, { message: "both columns should be empty" });

    await click(".o_kanban_renderer");

    expect("[data-bounce-button]").toHaveClass("o_catch_attention");
});

test.tags("mobile");
test("Should load grouped kanban with folded column", async () => {
    Product._records[1].fold = true;
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
                <kanban>
                    <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                    <templates>
                        <t t-name="card">
                            <field name="foo"/>
                        </t>
                    </templates>
                </kanban>`,
        groupBy: ["product_id"],
    });
    expect(".o_column_progress").toHaveCount(2, { message: "Should have 2 progress bar" });
    expect(".o_kanban_group").toHaveCount(2, { message: "Should have 2 grouped column" });
    expect(".o_kanban_record").toHaveCount(2, { message: "Should have 2 loaded record" });
    expect(".o_kanban_load_more").toHaveCount(1, {
        message: "Should have a folded column with a load more button",
    });
    await contains(".o_kanban_load_more button").click();
    expect(".o_kanban_load_more").toHaveCount(0, { message: "Shouldn't have a load more button" });
    expect(".o_kanban_record").toHaveCount(4, { message: "Should have 4 loaded record" });
});

test("kanban records are middle clickable by default", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`opened in new window: ${url}`);
        },
    });
    patchWithCleanup(browser.sessionStorage, {
        setItem(key, value) {
            expect.step(`set ${key}-${value}`);
            super.setItem(key, value);
        },
        getItem(key) {
            const res = super.getItem(key);
            expect.step(`get ${key}-${res}`);
            return res;
        },
    });
    Partner._views["kanban,false"] = `
        <kanban>
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;
    Partner._views["search,false"] = "<search/>";
    Partner._views["form,false"] = `
        <form>
            <field name="product_id"/>
            <field name="foo"/>
        </form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
    });

    await contains(".o_kanban_record").click({ ctrlKey: true });
    expect.verifySteps([
        "get current_action-null",
        'set current_action-{"id":1,"res_model":"partner","type":"ir.actions.act_window","views":[[false,"kanban"],[false,"form"]]}',
        'get current_action-{"id":1,"res_model":"partner","type":"ir.actions.act_window","views":[[false,"kanban"],[false,"form"]]}',
        'set current_action-{"id":1,"res_model":"partner","type":"ir.actions.act_window","views":[[false,"kanban"],[false,"form"]]}',
        "opened in new window: /odoo/action-1/1",
        'set current_action-{"id":1,"res_model":"partner","type":"ir.actions.act_window","views":[[false,"kanban"],[false,"form"]]}',
    ]);
});

test("display 'None' for empty char field values in grouped Kanban view", async () => {
    Partner._records[0].foo = false;

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
        groupBy: ["foo"],
    });

    expect(".o_kanban_group:first-child .o_column_title").toHaveText("None\n(1)");
});

test("display '0' for empty int field values in grouped Kanban view", async () => {
    Partner._records[0].int_field = 0;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["int_field"],
    });

    expect(".o_kanban_group:first-child .o_column_title").toHaveText("0\n(1)");
});
