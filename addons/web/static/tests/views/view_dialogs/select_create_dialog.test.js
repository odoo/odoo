import { renderToMarkup } from "@web/core/utils/render";
import { useSetupAction } from "@web/search/action_hook";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { listView } from "@web/views/list/list_view";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { WebClient } from "@web/webclient/webclient";

import { xml } from "@odoo/owl";

import {
    clickModalButton,
    clickSave,
    contains,
    defineModels,
    editFavoriteName,
    fields,
    getService,
    models,
    mockService,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    removeFacet,
    saveFavorite,
    toggleMenuItem,
    toggleSaveFavorite,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";

class Partner extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    foo = fields.Char({ string: "Foo" });
    bar = fields.Boolean({ string: "Bar" });
    instrument = fields.Many2one({ string: "Instrument", relation: "instrument" });

    _records = [
        { id: 1, foo: "blip", name: "blipblip", bar: true },
        { id: 2, foo: "ta tata ta ta", name: "macgyver", bar: false },
        { id: 3, foo: "piou piou", name: "Jack O'Neill", bar: true },
    ];
}

class Instrument extends models.Model {
    name = fields.Char({ string: "name" });
    badassery = fields.Many2many({
        string: "level",
        relation: "badassery",
        domain: [["level", "=", "Awsome"]],
    });
}

class Badassery extends models.Model {
    level = fields.Char({ string: "level" });

    _records = [{ id: 1, level: "Awsome" }];
}

class Product extends models.Model {
    name = fields.Char({ string: "name" });
    partner = fields.One2many({ string: "Doors", relation: "partner" });

    _records = [{ id: 1, name: "The end" }];
}

class SaleOrderLine extends models.Model {
    _name = "sale_order_line";

    product_id = fields.Many2one({ string: "product_id", relation: "product" });
    linked_sale_order_line = fields.Many2many({
        string: "linked_sale_order_line",
        relation: "sale_order_line",
    });
}

defineModels([Partner, Instrument, Badassery, Product, SaleOrderLine]);

beforeEach(() => onRpc("has_group", () => true));

test.tags("desktop");
test("SelectCreateDialog use domain, group_by and search default on desktop", async () => {
    expect.assertions(3);
    Partner._views["list"] = /* xml */ `
        <list string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = /* xml */ `
        <search>
            <field name="foo" filter_domain="[('name','ilike',self), ('foo','ilike',self)]"/>
            <group expand="0" string="Group By">
                <filter name="groupby_bar" context="{'group_by' : 'bar'}"/>
            </group>
        </search>
    `;
    let search = 0;
    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs).toMatchObject(
            {
                domain: [
                    "&",
                    ["name", "like", "a"],
                    "&",
                    ["name", "ilike", "piou"],
                    ["foo", "ilike", "piou"],
                ],
                aggregates: ["__count"],
                groupby: ["bar"],
                order: "",
                limit: 80,
                offset: 0,
            },
            {
                message:
                    "should search with the complete domain (domain + search), and group by 'bar'",
            }
        );
    });
    onRpc("web_search_read", ({ kwargs }) => {
        if (search === 0) {
            expect(kwargs).toMatchObject(
                {
                    domain: [
                        "&",
                        ["name", "like", "a"],
                        "&",
                        ["name", "ilike", "piou"],
                        ["foo", "ilike", "piou"],
                    ],
                    specification: { name: {}, foo: {} },
                    limit: 80,
                    offset: 0,
                    order: "",
                    count_limit: 10001,
                },
                {
                    message: "should search with the complete domain (domain + search)",
                }
            );
        } else if (search === 1) {
            expect(kwargs).toMatchObject(
                {
                    domain: [["name", "like", "a"]],
                    specification: { name: {}, foo: {} },
                    limit: 80,
                    offset: 0,
                    order: "",
                    count_limit: 10001,
                },
                {
                    message: "should search with the domain",
                }
            );
        }
        search++;
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        noCreate: true,
        resModel: "partner",
        domain: [["name", "like", "a"]],
        context: {
            search_default_groupby_bar: true,
            search_default_foo: "piou",
        },
    });
    await animationFrame();
    await removeFacet("Bar");
    await removeFacet("Foo piou");
});

test.tags("mobile");
test("SelectCreateDialog use domain, group_by and search default on mobile", async () => {
    expect.assertions(3);
    Partner._views["search"] = /* xml */ `
        <search>
            <field name="foo" filter_domain="[('name','ilike',self), ('foo','ilike',self)]"/>
            <group expand="0" string="Group By">
                <filter name="groupby_bar" context="{'group_by' : 'bar'}"/>
            </group>
        </search>
    `;
    Partner._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/><field name="foo"/></t></templates></kanban>`;
    let search = 0;
    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs).toMatchObject(
            {
                context: {
                    read_group_expand: true,
                },
                domain: [
                    "&",
                    ["name", "like", "a"],
                    "&",
                    ["name", "ilike", "piou"],
                    ["foo", "ilike", "piou"],
                ],
                groupby: ["bar"],
                aggregates: ["__count"],
                offset: 0,
                order: "",
            },
            {
                message:
                    "should search with the complete domain (domain + search), and group by 'bar'",
            }
        );
    });
    onRpc("web_search_read", ({ kwargs }) => {
        if (search === 0) {
            expect(kwargs).toMatchObject(
                {
                    domain: [
                        "&",
                        ["name", "like", "a"],
                        "&",
                        ["name", "ilike", "piou"],
                        ["foo", "ilike", "piou"],
                    ],
                    specification: { name: {}, foo: {} },
                    limit: 40,
                    offset: 0,
                    order: "",
                    count_limit: 10001,
                },
                { message: "should search with the complete domain (domain + search)" }
            );
        } else if (search === 1) {
            expect(kwargs).toMatchObject(
                {
                    domain: [["name", "like", "a"]],
                    specification: { name: {}, foo: {} },
                    limit: 40,
                    offset: 0,
                    order: "",
                    count_limit: 10001,
                },
                { message: "should search with the domain" }
            );
        }
        search++;
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        noCreate: true,
        resModel: "partner",
        domain: [["name", "like", "a"]],
        context: {
            search_default_groupby_bar: true,
            search_default_foo: "piou",
        },
    });
    await animationFrame();
    await removeFacet("Bar");
    await removeFacet("Foo piou");
});

test("SelectCreateDialog correctly evaluates domains", async () => {
    expect.assertions(1);

    Partner._views["list"] = /* xml */ `
        <list string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = /* xml */ `<search><field name="foo"/></search>`;
    Partner._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/><field name="foo"/></t></templates></kanban>`;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["id", "=", 2]], {
            message: "should have correctly evaluated the domain",
        });
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        noCreate: true,
        resModel: "partner",
        domain: [["id", "=", 2]],
    });
    await animationFrame();
});

test.tags("desktop");
test("SelectCreateDialog list view is readonly", async () => {
    Partner._fields.sequence = fields.Integer();
    Partner._views["list"] = /* xml */ `
        <list string="Partner" editable="bottom">
            <field name="sequence" widget="handle"/>
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;

    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
    });
    await animationFrame();

    // click on the first row to see if the list is editable
    await contains(".o_list_view tbody tr td:first").click();

    expect(".o_list_view tbody tr td .o_field_char input").toHaveCount(0, {
        message: "list view should not be editable in a SelectCreateDialog",
    });
    expect(".o_handle_cell").toHaveCount(4);
    expect(".o_row_handle.o_disabled").toHaveCount(3, {
        message: "handles should be disabled in readonly",
    });
});

test.tags("desktop");
test("SelectCreateDialog cascade x2many in create mode on desktop", async () => {
    expect.assertions(5);

    Partner._views["form"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="instrument" widget="one2many" mode="list"/>
        </form>
    `;
    Instrument._views["form"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="badassery">
                <list>
                    <field name="level"/>
                </list>
            </field>
        </form>
    `;
    Badassery._views["list"] = /* xml */ `<list><field name="level"/></list>`;
    Badassery._views["search"] = /* xml */ `<search><field name="level"/></search>`;

    onRpc(["partner", "instrument"], "get_formview_id", () => false);
    onRpc("instrument", "web_save", ({ args }) => {
        expect(args[1]).toEqual(
            { badassery: [[4, 1]], name: "ABC" },
            {
                message: "The method create should have been called with the right arguments",
            }
        );
        return [{ id: 90 }];
    });

    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner" widget="one2many" >
                    <list editable="top">
                        <field name="name"/>
                        <field name="instrument"/>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=instrument] input").edit("ABC", { confirm: false });
    await runAllTimers();
    await contains(
        `[name="instrument"] .dropdown .dropdown-menu li:contains("Create and edit...")`
    ).click();

    expect(".modal .modal-lg").toHaveCount(1);

    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal .modal-lg").toHaveCount(2);

    await contains(".modal .o_data_row input[type=checkbox]").check();
    await clickModalButton({ text: "Select" });

    expect(".modal .modal-lg").toHaveCount(1);
    expect(".modal .o_data_cell").toHaveText("Awsome");

    // click on modal save button
    await clickSave({ index: 1 });
});

test.tags("mobile");
test("SelectCreateDialog cascade x2many in create mode on mobile", async () => {
    expect.assertions(5);

    Partner._views["form"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="instrument" widget="one2many" mode="list"/>
        </form>
    `;
    Instrument._views["form"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="badassery">
                <list>
                    <field name="level"/>
                </list>
            </field>
        </form>
    `;
    Instrument._views["search"] = /* xml */ `<search/>`;
    Instrument._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`;
    Badassery._views["search"] = /* xml */ `<search/>`;
    Badassery._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="level"/></t></templates></kanban>`;

    onRpc(["partner", "instrument"], "get_formview_id", () => false);
    onRpc("instrument", "web_save", ({ args }) => {
        expect(args[1]).toEqual(
            { badassery: [[4, 1]], name: "ABC" },
            { message: "The method create should have been called with the right arguments" }
        );
        return [{ id: 90 }];
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner" widget="one2many" >
                    <list editable="top">
                        <field name="name"/>
                        <field name="instrument"/>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(".o_field_x2many_list_row_add a").click();

    click(".o_field_widget[name=instrument] input");
    await animationFrame();

    await contains(`.modal .o_create_button`).click();

    expect(".modal .modal-lg").toHaveCount(2);

    await contains(".modal .o_field_char[name=name] input").edit("ABC");
    await contains(".modal .o_field_x2many_list_row_add a").click();

    expect(".modal .modal-lg").toHaveCount(3);
    await contains(
        ".modal .o_data_row input[type=checkbox], .o_kanban_record:contains(Awsome)"
    ).click();

    expect(".modal .modal-lg").toHaveCount(2);
    expect(".modal .o_data_cell").toHaveText("Awsome");

    // click on modal save button
    await clickSave({ index: 1 });
});

test.tags("desktop");
test("SelectCreateDialog: save current search on desktop", async () => {
    expect.assertions(5);
    Partner._views["list"] = /* xml */ `<list><field name="name"/> </list>`;
    Partner._views[
        "search"
    ] = /* xml */ `<search><filter name="bar" help="Bar" domain="[('bar', '=', True)]"/></search>`;

    patchWithCleanup(listView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            useSetupAction({
                getContext: () => ({ shouldBeInFilterContext: true }),
            });
        },
    });

    onRpc("get_views", ({ kwargs }) => {
        expect(kwargs.options.load_filters).toBe(true, { message: "Missing load_filters option" });
    });
    onRpc("create_or_replace", ({ model, args }) => {
        if (model === "ir.filters") {
            const irFilter = args[0];
            expect(irFilter.domain).toBe(`[("bar", "=", True)]`, {
                message: "should save the correct domain",
            });
            const expectedContext = {
                group_by: [], // default groupby is an empty list
                shouldBeInFilterContext: true,
            };
            expect(irFilter.context).toEqual(expectedContext, {
                message: "should save the correct context",
            });
            return [7]; // fake serverSideId
        }
    });

    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        context: { shouldNotBeInFilterContext: false },
        resModel: "partner",
    });
    await animationFrame();

    expect(".o_data_row").toHaveCount(3, { message: "should contain 3 records" });

    // filter on bar
    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");

    expect(".o_data_row").toHaveCount(2, { message: "should contain 2 records" });

    // save filter
    await toggleSaveFavorite();
    await editFavoriteName("some name");
    await saveFavorite();
});

test.tags("mobile");
test("SelectCreateDialog: save current search on mobile", async () => {
    expect.assertions(5);
    Partner._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`;
    Partner._views[
        "search"
    ] = /* xml */ `<search><filter name="bar" help="Bar" domain="[('bar', '=', True)]"/></search>`;

    patchWithCleanup(kanbanView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            useSetupAction({
                getContext: () => ({ shouldBeInFilterContext: true }),
            });
        },
    });

    onRpc("get_views", ({ kwargs }) => {
        expect(kwargs.options.load_filters).toBe(true, { message: "Missing load_filters option" });
    });
    onRpc("create_or_replace", ({ model, args }) => {
        if (model === "ir.filters") {
            const irFilter = args[0];
            expect(irFilter.domain).toBe(`[("bar", "=", True)]`, {
                message: "should save the correct domain",
            });
            const expectedContext = {
                group_by: [], // default groupby is an empty list
                shouldBeInFilterContext: true,
            };
            expect(irFilter.context).toEqual(expectedContext, {
                message: "should save the correct context",
            });
            return 7; // fake serverSideId
        }
    });

    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        context: { shouldNotBeInFilterContext: false },
        resModel: "partner",
    });
    await animationFrame();

    expect(".o_kanban_record[data-id]").toHaveCount(3, { message: "should contain 3 records" });

    // filter on bar
    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");

    expect(".o_kanban_record[data-id]").toHaveCount(2, { message: "should contain 2 records" });

    // save filter
    await toggleSaveFavorite();
    await editFavoriteName("some name");
    await saveFavorite();
});

test.tags("desktop");
test("SelectCreateDialog calls on_selected with every record matching the domain", async () => {
    expect.assertions(1);

    Partner._views["list"] = /* xml */ `
        <list limit="2" string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = /* xml */ `<search><field name="foo"/></search>`;

    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
        onSelected: (records) => expect(records.join(",")).toBe("1,2,3"),
    });
    await animationFrame();

    await contains("thead .o_list_record_selector input").click();
    await contains(".o_selection_box .o_select_domain").click();
    await clickModalButton({ text: "Select" });
});

test.tags("desktop");
test("SelectCreateDialog calls on_selected with every record matching without selecting a domain", async () => {
    expect.assertions(1);
    Partner._views["list"] = /* xml */ `
        <list limit="2" string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = /* xml */ `<search><field name="foo"/></search>`;

    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
        onSelected: (records) => expect(records.join(",")).toBe("1,2"),
    });
    await animationFrame();

    await contains("thead .o_list_record_selector input").click();
    await contains(".o_selection_box").click();
    await clickModalButton({ text: "Select", index: 1 });
});

test.tags("desktop");
test("SelectCreateDialog: multiple clicks on record", async () => {
    Partner._views["list"] = /* xml */ `<list><field name="name"/></list>`;
    Partner._views["search"] = /* xml */ `<search><field name="foo"/></search>`;

    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
        onSelected: async function (records) {
            expect.step(`select record ${records[0]}`);
        },
    });
    await animationFrame();
    await click(".modal .o_data_row .o_data_cell");
    await click(".modal .o_data_row .o_data_cell");
    await click(".modal .o_data_row .o_data_cell");
    await animationFrame();
    // should have called onSelected only once
    expect.verifySteps(["select record 1"]);
});

test.tags("desktop");
test("SelectCreateDialog: default props, create a record on desktop", async () => {
    Partner._views["list"] = /* xml */ `<list><field name="name"/></list>`;
    Partner._views["search"] = /* xml */ `
        <search>
            <filter name="bar" help="Bar" domain="[('bar', '=', True)]"/>
        </search>
    `;
    Partner._views["form"] = /* xml */ `<form><field name="name"/></form>`;
    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        onSelected: (resIds) => expect.step(`onSelected ${resIds}`),
        resModel: "partner",
    });
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_list_view .o_data_row").toHaveCount(3);
    expect(".o_dialog footer button").toHaveCount(3);
    expect(".o_dialog footer button.o_select_button").toHaveCount(1);
    expect(".o_dialog footer button.o_create_button").toHaveCount(1);
    expect(".o_dialog footer button.o_form_button_cancel").toHaveCount(1);
    expect(".o_dialog .o_control_panel_main_buttons .o_list_button_add").toHaveCount(0);

    await contains(".o_dialog footer button.o_create_button").click();

    expect(".o_dialog").toHaveCount(2);
    expect(".o_dialog .o_form_view").toHaveCount(1);

    await contains(".o_dialog .o_form_view .o_field_widget input").edit("hello");
    await clickSave();

    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps(["onSelected 4"]);
});

test.tags("mobile");
test("SelectCreateDialog: default props, create a record on mobile", async () => {
    Partner._views["search"] = /* xml */ `
        <search>
            <filter name="bar" help="Bar" domain="[('bar', '=', True)]"/>
        </search>
    `;
    Partner._views["kanban"] = /* xml */ `
        <kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`;
    Partner._views["form"] = /* xml */ `<form><field name="name"/></form>`;
    await mountWithCleanup(WebClient);

    getService("dialog").add(SelectCreateDialog, {
        onSelected: (resIds) => expect.step(`onSelected ${resIds}`),
        resModel: "partner",
    });
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_kanban_record[data-id]").toHaveCount(3);
    expect(".o_dialog footer button").toHaveCount(3);
    expect(".o_dialog footer button.o_select_button").toHaveCount(1);
    expect(".o_dialog footer button.o_create_button").toHaveCount(1);
    expect(".o_dialog footer button.o_form_button_cancel").toHaveCount(1);
    expect(".o_dialog .o_control_panel_main_buttons .o_list_button_add").toHaveCount(0);

    await contains(".o_dialog footer button.o_create_button").click();

    expect(".o_dialog").toHaveCount(2);
    expect(".o_dialog .o_form_view").toHaveCount(1);

    await contains(".o_dialog .o_form_view .o_field_widget input").edit("hello");
    await clickSave();

    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps(["onSelected 4"]);
});

test.tags("desktop");
test("SelectCreateDialog empty list, default no content helper", async () => {
    Partner._records = [];
    Partner._views["list"] = /* xml */ `
        <list>
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, { resModel: "partner" });
    await animationFrame();
    expect(".o_dialog .o_list_view").toHaveCount(1);
    expect(".o_dialog .o_list_view .o_data_row").toHaveCount(0);
    expect(".o_dialog .o_list_view .o_view_nocontent").toHaveCount(1);
    expect(queryOne(".o_dialog .o_list_view .o_view_nocontent")).toHaveInnerHTML(
        `<div class="o_nocontent_help"><p>No record found</p><p>Adjust your filters or create a new record.</p></div>`
    );
});
test.tags("mobile");
test("SelectCreateDialog empty kanban, default no content helper", async () => {
    Partner._records = [];
    Partner._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`;
    Partner._views["search"] = /* xml */ `<search/>`;
    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, { resModel: "partner" });
    await animationFrame();
    expect(".o_dialog .o_kanban_view").toHaveCount(1);
    expect(".o_dialog .o_kanban_view .o_kanban_record[data-id]").toHaveCount(0);
    expect(".o_dialog .o_kanban_view .o_view_nocontent").toHaveCount(1);
    expect(queryOne(".o_dialog .o_kanban_view .o_view_nocontent")).toHaveInnerHTML(
        `<div class="o_nocontent_help"><p>No record found</p><p>Adjust your filters or create a new record.</p></div>`
    );
});

test.tags("desktop");
test("SelectCreateDialog empty list, noContentHelp props", async () => {
    Partner._records = [];
    Partner._views["list"] = /* xml */ `
        <list>
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;

    await mountWithCleanup(WebClient);
    const template = xml`
            <p class="custom_classname">Hello</p>
            <p>I'm an helper</p>
        `;
    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
        noContentHelp: renderToMarkup(template),
    });
    await animationFrame();

    expect(".o_dialog .o_list_view").toHaveCount(1);
    expect(".o_dialog .o_list_view .o_data_row").toHaveCount(0);
    expect(".o_dialog .o_list_view .o_view_nocontent").toHaveCount(1);
    expect(queryOne(".o_dialog .o_list_view .o_view_nocontent")).toHaveInnerHTML(
        `<div class="o_nocontent_help"><p class="custom_classname">Hello</p><p>I'm an helper</p></div>`
    );
});

test.tags("desktop");
test("SelectCreateDialog with open action", async () => {
    Instrument._records = [];
    for (let i = 0; i < 25; i++) {
        Instrument._records.push({
            id: i + 1,
            name: "Instrument " + i,
        });
    }
    mockService("action", {
        doActionButton(params) {
            const { name } = params;
            expect.step(`execute_action: ${name}`, params);
        },
    });
    Instrument._views["list"] = /* xml */ `
        <list action="test_action" type="object">
            <field name="name"/>
        </list>
    `;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="instrument"/>
            </form>
        `,
    });
    await contains(`.o_field_widget[name="instrument"] .dropdown input`).click();
    await contains(`.o_field_widget[name="instrument"] .o_m2o_dropdown_option_search_more`).click();
    await contains(
        `.o_list_renderer .o_data_row .o_field_cell.o_list_char[data-tooltip="Instrument 10"]`
    ).click();
    expect("input").toHaveValue("Instrument 10");
    expect.verifySteps([]);
});

test.tags("mobile");
test("SelectCreateDialog empty kanban, noContentHelp props", async () => {
    Partner._records = [];
    Partner._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`;
    Partner._views["search"] = /* xml */ `<search/>`;

    await mountWithCleanup(WebClient);
    const template = xml`
            <p class="custom_classname">Hello</p>
            <p>I'm an helper</p>
        `;
    getService("dialog").add(SelectCreateDialog, {
        resModel: "partner",
        noContentHelp: renderToMarkup(template),
    });
    await animationFrame();

    expect(".o_dialog .o_kanban_view").toHaveCount(1);
    expect(".o_dialog .o_kanban_view .o_kanban_record[data-id]").toHaveCount(0);
    expect(".o_dialog .o_kanban_view .o_view_nocontent").toHaveCount(1);
    expect(queryOne(".o_dialog .o_kanban_view .o_view_nocontent")).toHaveInnerHTML(
        `<div class="o_nocontent_help"><p class="custom_classname">Hello</p><p>I'm an helper</p></div>`
    );
});

test.tags("mobile");
test("SelectCreateDialog: clear selection on mobile", async () => {
    expect.assertions(3);
    SaleOrderLine._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="id"/></t></templates></kanban>`;
    Product._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="id"/><field name="name"/></t></templates></kanban>`;
    Product._views["search"] = /* xml */ `<search/>`;

    onRpc("web_save", ({ model, args }) => {
        if (model === "sale_order_line") {
            expect(args[1].product_id).toBe(false, {
                message: `there should be no product selected`,
            });
        }
    });

    await mountView({
        type: "form",
        resModel: "sale_order_line",
        arch: `
                <form>
                    <field name="product_id"/>
                    <field name="linked_sale_order_line" widget="many2many_tags"/>
                </form>`,
    });

    await contains('.o_field_widget[name="linked_sale_order_line"] input').click();
    expect(".modal-dialog.modal-lg:eq(0) .btn.o_clear_button").toHaveCount(0, {
        message: "there shouldn't be a Clear button",
    });
    await contains(".modal-dialog.modal-lg:eq(0) .o_form_button_cancel").click();

    // Select a product
    await contains('.o_field_widget[name="product_id"] input').click();
    await contains(".modal-dialog.modal-lg:eq(0) .o_kanban_record:nth-child(1)").click();

    // Remove the product
    await contains('.o_field_widget[name="product_id"] input').click();
    expect(".modal-dialog.modal-lg:eq(0) .btn.o_clear_button").toHaveCount(1, {
        message: "there should be a Clear button",
    });
    await contains(".btn.o_clear_button").click();

    await clickSave();
});

test.tags("mobile");
test("SelectCreateDialog: selection_mode should be true", async () => {
    expect.assertions(3);
    Product._views["kanban"] = /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                         <div class="o_primary" t-if="!selection_mode">
                            <a type="object" name="some_action">
                                <field name="name"/>
                            </a>
                         </div>
                         <div class="o_primary" t-if="selection_mode">
                             <field name="name"/>
                         </div>
                    </t>
                </templates>
            </kanban>`;
    Product._views["search"] = /* xml */ `<search/>`;

    onRpc("web_save", ({ model, args }) => {
        if (model === "sale_order_line") {
            expect(args[1].product_id).toBe(1, {
                message: `the product should be selected`,
            });
        }
    });
    await mountView({
        type: "form",
        resModel: "sale_order_line",
        arch: `
            <form>
                <field name="product_id"/>
                <field name="linked_sale_order_line" widget="many2many_tags"/>
            </form>`,
    });

    await contains('.o_field_widget[name="product_id"] input').click();
    await contains(".modal-dialog.modal-lg .o_kanban_record:nth-child(1) .o_primary span").click();
    expect(".modal-dialog.modal-lg").toHaveCount(0);
    await clickSave();
    expect.verifySteps([]);
});

test.tags("mobile");
test("SelectCreateDialog: default props, create a record", async () => {
    Product._views["form"] = /* xml */ `<form><field name="name"/></form>`;
    Product._views[
        "kanban"
    ] = /* xml */ `<kanban><templates><t t-name="card"><field name="id"/><field name="name"/></t></templates></kanban>`;
    Product._views["search"] = /* xml */ `<search/>`;

    await mountView({
        type: "form",
        resModel: "sale_order_line",
        arch: `
            <form>
                <field name="product_id"/>
                <field name="linked_sale_order_line" widget="many2many_tags"/>
            </form>`,
    });

    await contains('.o_field_widget[name="product_id"] input').click();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_dialog footer button").toHaveCount(2);
    expect(".o_dialog footer button.o_create_button").toHaveCount(1);
    expect(".o_dialog footer button.o_form_button_cancel").toHaveCount(1);
    expect(".o_dialog .o_control_panel_main_buttons .o-kanban-button-new").toHaveCount(0);

    await contains(".o_dialog footer button.o_create_button:eq(0)").click();

    expect(".o_dialog").toHaveCount(2);
    expect(".o_dialog .o_form_view").toHaveCount(1);

    await contains(".o_dialog .o_form_view .o_field_widget input").edit("hello");
    await contains(".o_dialog .o_form_button_save:eq(0)").click();

    expect(".o_dialog").toHaveCount(0);
});
