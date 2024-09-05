import { after, beforeEach, expect, test } from "@odoo/hoot";
import {
    click,
    dblclick,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryText,
    setInputFiles,
} from "@odoo/hoot-dom";
import { FileInput } from "@web/core/file_input/file_input";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, onRendered, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    getDropdownMenu,
    getKanbanColumn,
    getKanbanColumnDropdownMenu,
    getKanbanRecord,
    getKanbanRecordTexts,
    getService,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    stepAllNetworkCalls,
    toggleKanbanColumnActions,
    toggleKanbanRecordDropdown,
    validateSearch,
    webModels,
} from "@web/../tests/web_test_helpers";

import { currencies } from "@web/core/currency";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getOrigin } from "@web/core/utils/urls";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ViewButton } from "@web/views/view_button/view_button";
import { AnimatedNumber } from "@web/views/view_components/animated_number";
import { WebClient } from "@web/webclient/webclient";

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

    // avoid "kanban-box" deprecation warnings in this suite, which defines legacy kanban on purpose
    const originalConsoleWarn = console.warn;
    patchWithCleanup(console, {
        warn: (msg) => {
            if (msg !== "'kanban-box' is deprecated, use 'kanban-card' API instead") {
                originalConsoleWarn(msg);
            }
        },
    });
});

test("display full is supported on fields", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
        <kanban class="o_kanban_test">
            <templates>
                <t t-name="kanban-box">
                    <field name="foo" display="full"/>
                </t>
            </templates>
        </kanban>`,
    });

    expect(".o_kanban_record span.o_text_block").toHaveCount(4);
    expect(queryFirst("span.o_text_block").textContent).toBe("yop");
});

test.tags("desktop")("basic grouped rendering", async () => {
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
                <field name="bar" />
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo" />
                        </div>
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
                <field name="bar" />
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo" />
                        </div>
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
                <field name="active"/>
                <field name="bar"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
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

test("context can be used in kanban template", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                    <div>
                        <t t-if="context.some_key">
                            <field name="foo"/>
                        </t>
                    </div>
                    </t>
                </templates>
            </kanban>`,
        context: { some_key: 1 },
        domain: [["id", "=", 1]],
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record span:contains(yop)").toHaveCount(1);
});

test("user context can be used in kanban template", async () => {
    patchWithCleanup(user, { context: { some_key: true } });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="kanban-box">
                        <field t-if="user_context.some_key" name="foo"/>
                    </div>
                </templates>
            </kanban>`,
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
                    <t t-name="kanban-box">
                        <div>
                            <t t-call="another-template"/>
                        </div>
                    </t>
                    <t t-name="another-template">
                        <span><field name="foo"/></span>
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
                    <t t-name="kanban-box">
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
                    <t t-name="kanban-box">
                        <div>
                            <field t-if="record.int_field.value > -1" name="int_field"/>
                            <t t-else="">Negative value</t>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field t-if="record.int_field.value > -1" name="int_field" widget="integer"/>
                            <t t-else="">Negative value</t>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="int_field" widget="my_field"
                                t-att-dyn-bool="record.foo.value.length > 3"
                                t-attf-interp-str="hello {{record.foo.value}}"
                                t-attf-interp-str2="hello #{record.foo.value} !"
                                t-attf-interp-str3="hello {{record.foo.value}} }}"
                            />
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <a name="one" type="object" class="hola"/>
                            <a name="two" type="object" class="hola" t-attf-class="hello"/>
                            <a name="sri" type="object" class="hola" t-attf-class="{{record.foo.value}}"/>
                            <a name="foa" type="object" class="hola" t-attf-class="{{record.foo.value}} olleh"/>
                            <a name="fye" type="object" class="hola" t-attf-class="hello {{record.foo.value}}"/>
                        </div>
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

test("click on a button type='delete' to delete a record in a column", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban limit="3">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <div><a role="menuitem" type="delete" class="dropdown-item o_delete">Delete</a></div>
                            <field name="foo"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <div><a role="menuitem" type="archive" class="dropdown-item o_archive">archive</a></div>
                            <field name="foo"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <div><a role="menuitem" type="unarchive" class="dropdown-item o_unarchive">unarchive</a></div>
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(queryAll(".o_kanban_record", { root: getKanbanColumn(0) })).toHaveCount(2);

    await contains(".o_kanban_record .o_unarchive").click();

    expect.verifySteps(["unarchive:1"]);
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="category_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                            <field name="foo"/>
                            <field name="state" widget="priority"/>
                        </div>
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
    const tag = queryFirst(".o_kanban_record:nth-child(2) .o_tag");
    expect(tag.innerText).toBe("silver");

    // Write on the record using the priority widget to trigger a re-render in readonly
    await contains(".o_kanban_record:first-child .o_priority_star:first-child").click();

    expect.verifySteps(["web_save"]);
    expect(".o_kanban_record:first-child .o_field_many2many_tags .o_tag").toHaveCount(2, {
        message: "first record should still contain only 2 tags",
    });
    const tags = queryAll(".o_kanban_record:first-child .o_tag");
    expect(tags[0].innerText).toBe("gold");
    expect(tags[1].innerText).toBe("silver");

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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                            <field name="state" widget="priority"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                            <div>
                                <a class="o_test_link" href="#">test link</a>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_kanban_record a").toHaveCount(1);

    const testLink = queryFirst(".o_kanban_record a");
    expect(!!testLink.href).toBe(true, {
        message: "link inside kanban record should have non-empty href",
    });

    // Prevent the browser default behaviour when clicking on anything.
    // This includes clicking on a `<a>` with `href`, so that it does not
    // change the URL in the address bar.
    // Note that we should not specify a click listener on 'a', otherwise
    // it may influence the kanban record global click handler to not open
    // the record.
    testLink.addEventListener("click", (ev) => {
        expect(ev.defaultPrevented).toBe(false, {
            message: "should not prevented browser default behaviour beforehand",
        });
        expect(ev.target).toBe(testLink, {
            message: "should have clicked on the test link in the kanban record",
        });
        ev.preventDefault();
    });

    await click(testLink);
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="salary" widget="monetary"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect(resId).toBe(1, { message: "should trigger an event to open the form view" });
        },
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4);

    await click(queryFirst(".o_field_monetary[name=salary]"));
});

test("clicking on a link triggers correct event", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div><a type="edit">Edit</a></div>
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
                <field name="product_id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="int_field"/>
                            <field name="category_ids" widget="many2many_tags"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["product_id"],
    });

    expect(".o_kanban_group").toHaveCount(2, { message: "there should be 2 'real' columns" });
    expect(queryFirst(".o_content")).toHaveClass("o_view_sample_data");
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
                    <div t-name="kanban-box">
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
                    <div t-name="kanban-box">
                        <field name="foo"/>
                        <a type="action" name="42" class="btn-primary" style="margin-left: 10px"><i class="oi oi-arrow-right"/> Click me !</a>
                    </div>
                </templates>
            </kanban>`,
    });

    await click(queryFirst("a[type='action']"));
    expect(queryFirst("a[type='action']")).toHaveClass("btn-primary");
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
                    <div t-name="kanban-box">
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
                <field name="active"/>
                <templates>
                    <div t-name="kanban-box">
                        <field name="foo"/>
                        <button type="object" name="a1" />
                        <button type="object" name="toggle_active" class="toggle-active" />
                    </div>
                </templates>
            </kanban>`,
    });

    expect(queryText("span", { root: getKanbanRecord({ index: 0 }) })).toBe("yop", {
        message: "should display 'yop' record",
    });
    await contains("button.toggle-active", { root: getKanbanRecord({ index: 0 }) }).click();
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo" invisible="id == 1"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo" widget="char" class="hi"/>
                        </div>
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
                <field name="date"/>
                <field name="datetime"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <span class="date" t-esc="record.date.value"/>
                            <span class="datetime" t-esc="record.datetime.value"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 0 }).querySelector(".date").innerText).toBe("01/25/2017");
    expect(getKanbanRecord({ index: 1 }).querySelector(".datetime").innerText).toBe(
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
                    <t t-name="kanban-box">
                        <div>
                            <span class="date" t-esc="record.date.raw_value"/>
                            <span class="datetime" t-esc="record.datetime.raw_value"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 0 }).querySelector(".date").innerText).toBe(
        "2017-01-25T00:00:00.000+01:00"
    );
    expect(getKanbanRecord({ index: 1 }).querySelector(".datetime").innerText).toBe(
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
            <field name="product_id"/>
            <templates>
                <t t-name="kanban-box">
                    <div>
                        <span class="product_id" t-esc="record.product_id.value"/>
                    </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <span class="product_id" t-esc="record.product_id.raw_value"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <button t-if="!record.product_id.raw_value" class="btn_a">A</button>
                            <button t-if="!record.category_ids.raw_value.length" class="btn_b">B</button>
                        </div>
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

test("properly evaluate more complex domains", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <field name="bar"/>
                <field name="category_ids"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                            <button type="object" invisible="bar or category_ids" class="btn btn-primary float-end" name="arbitrary">Join</button>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect("button.float-end.oe_kanban_action").toHaveCount(1, {
        message: "only one button should be visible",
    });
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
                <field name="foo"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <t t-esc="record.foo.value"/>
                            <widget name="test"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(getKanbanRecord({ index: 2 }).querySelector(".o_widget").innerText).toBe(
        '{"foo":"gnap"}'
    );
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
                <field name="foo"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <div class="foo" t-esc="record.foo.value"/>
                            <widget name="test"/>
                        </div>
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

test("test displaying image (URL, image field not set)", async () => {
    patchWithCleanup(KanbanCompiler.prototype, {
        compileImage(el) {
            el.setAttribute("t-att-data-src", el.getAttribute("t-att-src"));
            el.removeAttribute("t-att-src");
            return super.compileImage(el);
        },
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <img t-att-src="kanban_image('partner', 'image', record.id.raw_value)"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    // since the field image is not set, kanban_image will generate an URL
    expect(queryAll(`.o_kanban_record img`).map((img) => img.dataset.src.split("?")[0])).toEqual([
        `${getOrigin()}/web/image/partner/1/image`,
        `${getOrigin()}/web/image/partner/2/image`,
        `${getOrigin()}/web/image/partner/3/image`,
        `${getOrigin()}/web/image/partner/4/image`,
    ]);
    expect(queryFirst(".o_kanban_record img").loading).toBe("lazy");
});

test("test displaying image (write_date field)", async () => {
    // the presence of write_date field ensures that the image is reloaded when necessary
    expect.assertions(2);

    patchWithCleanup(KanbanCompiler.prototype, {
        compileImage(el) {
            el.setAttribute("t-att-data-src", el.getAttribute("t-att-src"));
            el.removeAttribute("t-att-src");
            return super.compileImage(el);
        },
    });

    const rec = Partner._records.find((r) => r.id === 1);
    rec.write_date = "2022-08-05 08:37:00";

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.specification).toEqual({ id: {}, write_date: {} });
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="id"/>
                <templates>
                    <t t-name="kanban-box"><div>
                    <img t-att-src="kanban_image('partner', 'image', record.id.raw_value)"/>
                    </div></t>
                </templates>
            </kanban>`,
        domain: [["id", "in", [1]]],
    });

    expect(
        `.o_kanban_record img[data-src='${getOrigin()}/web/image/partner/1/image?unique=1659688620000']`
    ).toHaveCount(1);
});

test("test displaying image (binary & placeholder)", async () => {
    patchWithCleanup(KanbanCompiler.prototype, {
        compileImage(el) {
            el.setAttribute("t-att-data-src", el.getAttribute("t-att-src"));
            el.removeAttribute("t-att-src");
            return super.compileImage(el);
        },
    });

    Partner._fields.image = fields.Binary();
    Partner._records[0].image = "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="id"/>
                <field name="image"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <img t-att-src="kanban_image('partner', 'image', record.id.raw_value)"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAll(`.o_kanban_record img`).map((img) => img.dataset.src.split("?")[0])).toEqual([
        "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
        `${getOrigin()}/web/image/partner/2/image`,
        `${getOrigin()}/web/image/partner/3/image`,
        `${getOrigin()}/web/image/partner/4/image`,
    ]);
});

test("test displaying image (for another record)", async () => {
    patchWithCleanup(KanbanCompiler.prototype, {
        compileImage(el) {
            el.setAttribute("t-att-data-src", el.getAttribute("t-att-src"));
            el.removeAttribute("t-att-src");
            return super.compileImage(el);
        },
    });

    Partner._fields.image = fields.Binary();
    Partner._records[0].image = "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="id"/>
                <field name="image"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <img t-att-src="kanban_image('partner', 'image', 1)"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    // the field image is set, but we request the image for a specific id
    // -> for the record matching the ID, the base64 should be returned
    // -> for all the other records, the image should be displayed by url
    expect(queryAll(`.o_kanban_record img`).map((img) => img.dataset.src.split("?")[0])).toEqual([
        "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
        `${getOrigin()}/web/image/partner/1/image`,
        `${getOrigin()}/web/image/partner/1/image`,
        `${getOrigin()}/web/image/partner/1/image`,
    ]);
});

test("test displaying image from m2o field (m2o field not set)", async () => {
    patchWithCleanup(KanbanCompiler.prototype, {
        compileImage(el) {
            el.setAttribute("t-att-data-src", el.getAttribute("t-att-src"));
            el.removeAttribute("t-att-src");
            return super.compileImage(el);
        },
    });

    class FooPartner extends models.Model {
        _name = "foo.partner";

        name = fields.Char();
        partner_id = fields.Many2one({ relation: "partner" });

        _records = [
            { id: 1, name: "foo_with_partner_image", partner_id: 1 },
            { id: 2, name: "foo_no_partner" },
        ];
    }
    defineModels([FooPartner]);

    await mountView({
        type: "kanban",
        resModel: "foo.partner",
        arch: `
            <kanban>
                <templates>
                    <div t-name="kanban-box">
                        <field name="name"/>
                        <field name="partner_id"/>
                        <img t-att-src="kanban_image('partner', 'image', record.partner_id.raw_value)"/>
                    </div>
                </templates>
            </kanban>`,
    });

    expect(queryAll(`.o_kanban_record img`).map((img) => img.dataset.src.split("?")[0])).toEqual([
        `${getOrigin()}/web/image/partner/1/image`,
        `${getOrigin()}/web/image/partner/null/image`,
    ]);
});

test.tags("desktop")("set cover image", async () => {
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

    onRpc(({ model, method, args }) => {
        if (model === "partner" && method === "web_save") {
            expect.step(String(args[0][0]));
        }
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                            <div>
                                <field name="displayed_image_id" widget="attachment_image"/>
                            </div>
                        </div>
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
    expect.verifySteps(["1", "2"]);
});

test.tags("desktop")("open file explorer if no cover image", async () => {
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
                    <t t-name="kanban-menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="foo"/>
                            <div>
                                <field name="displayed_image_id" widget="attachment_image"/>
                            </div>
                        </div>
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

test.tags("desktop")("unset cover image", async () => {
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

    onRpc(({ model, method, args }) => {
        if (model === "partner" && method === "web_save") {
            expect.step(String(args[0][0]));
            expect(args[1].displayed_image_id).toBe(false);
        }
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-menu">
                        <a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>
                    </t>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                            <div>
                                <field name="displayed_image_id" widget="attachment_image"/>
                            </div>
                        </div>
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
    expect.verifySteps(["1", "2"]);
});

test.tags("desktop")("ungrouped kanban with handle field", async () => {
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="image" widget="image"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div><field name="bar"/></div>
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
                    <t t-name="kanban-box">
                        <div><field name="bar" widget="boolean"/></div>
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
                    <t t-name="kanban-box">
                        <div><field name="bar" widget="boolean_toggle"/></div>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(getKanbanRecord({ index: 0 }).querySelector("[name='bar'] input")).toBeChecked();
    expect(getKanbanRecord({ index: 1 }).querySelector("[name='bar'] input")).toBeChecked();

    await click(queryOne("[name='bar'] input", { root: getKanbanRecord({ index: 1 }) }));
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
                    <t t-name="kanban-box">
                        <div><field name="salary"/></div>
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

test("kanban with isHtmlEmpty method", async () => {
    Product._fields.description = fields.Html();
    Product._records.push({
        id: 11,
        name: "product 11",
        description: "<span class='text-info'>hello</hello>",
    });
    Product._records.push({
        id: 12,
        name: "product 12",
        description: "<p class='a'><span style='color:red;'/><br/></p>",
    });

    await mountView({
        type: "kanban",
        resModel: "product",
        arch: `
            <kanban>
                <field name="description"/>
                <templates>
                    <t t-name="kanban-box">
                    <div>
                        <field name="display_name"/>
                        <div class="test" t-if="!widget.isHtmlEmpty(record.description.raw_value)">
                            <t t-out="record.description.value"/>
                        </div>
                    </div>
                    </t>
                </templates>
            </kanban>`,
        domain: [["id", "in", [11, 12]]],
    });
    expect(".o_kanban_record:first-child div.test").toHaveCount(1, {
        message: "the container is displayed if description have actual content",
    });
    expect(queryText("span.text-info", { root: getKanbanRecord({ index: 0 }) })).toBe("hello", {
        message: "the inner html content is rendered properly",
    });
    expect(".o_kanban_record:last-child div.test").toHaveCount(0, {
        message:
            "the container is not displayed if description just have formatting tags and no actual content",
    });
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
                    <t t-name="kanban-box">
                        <div>
                            <widget name="widget_test_option" title="Widget with Option"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        resModel: "partner",
        type: "kanban",
    });

    expect(".o-test-widget-option").toHaveCount(4);
    expect(queryFirst(".o-test-widget-option").textContent).toBe("Widget with Option");
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
                    <t t-name="kanban-box">
                        <div>
                            <p>some value</p><field name="foo"/>
                        </div>
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
                    <t t-name="kanban-box">
                        <div>
                            <p>some value</p><field name="foo"/>
                        </div>
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
    patchWithCleanup(console, {
        warn: (msg) => {
            if (msg !== "'kanban-box' is deprecated, use 'kanban-card' API instead") {
                expect.step("warning");
            }
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <span t-foreach="[1, 2, 3]" t-as="i" t-esc="i" />
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect.verifySteps(["warning"]);
    expect(getKanbanRecord({ index: 0 }).innerText).toBe("123");
});

test("Allow use of 'editable'/'deletable' in ungrouped kanban", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban on_create="quick_create">
                <templates>
                    <div t-name="kanban-box">
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

test("can use JSON in kanban template", async () => {
    Partner._records = [{ id: 1, foo: '["g", "e", "d"]' }];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="kanban-box">
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

test("Can't use KanbanRecord implementation details in arch", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
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
    expect(queryFirst(".o_kanban_record").innerHTML).toBe("<div></div>");
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
                <t t-name="kanban-box">
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
