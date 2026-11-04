import { renderToMarkup } from "@web/core/utils/render";
import { useSetupAction } from "@web/search/action_hook";
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

import { beforeEach, describe, expect, test } from "@odoo/hoot";
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

defineModels([Partner, Instrument, Badassery, Product]);

describe.current.tags("desktop");

beforeEach(() => onRpc("has_group", () => true));

test("SelectCreateDialog use domain, group_by and search default", async () => {
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
                fields: [],
                groupby: ["bar"],
                orderby: "",
                lazy: true,
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

test("SelectCreateDialog correctly evaluates domains", async () => {
    expect.assertions(1);

    Partner._views["list"] = /* xml */ `
        <list string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = /* xml */ `<search><field name="foo"/></search>`;
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

test("SelectCreateDialog list view in readonly", async () => {
    Partner._views["list"] = /* xml */ `
        <list string="Partner" editable="bottom">
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
});

test("SelectCreateDialog cascade x2many in create mode", async () => {
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

    onRpc(async ({ route, args }) => {
        if (route === "/web/dataset/call_kw/partner/get_formview_id") {
            return false;
        }
        if (route === "/web/dataset/call_kw/instrument/get_formview_id") {
            return false;
        }
        if (route === "/web/dataset/call_kw/instrument/web_save") {
            expect(args[1]).toEqual(
                { badassery: [[4, 1]], name: "ABC" },
                {
                    message: "The method create should have been called with the right arguments",
                }
            );
            return [{ id: 90 }];
        }
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

test("SelectCreateDialog: save current search", async () => {
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
            return 7; // fake serverSideId
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
    await contains(".o_list_selection_box .o_list_select_domain").click();
    await clickModalButton({ text: "Select" });
});

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
    await contains(".o_list_selection_box").click();
    await clickModalButton({ text: "Select", index: 1 });
});

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

test("SelectCreateDialog: default props, create a record", async () => {
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

test("SelectCreateDialog: enable select when grouped with domain selection", async () => {
    Partner._views["list"] = `
        <list string="Partner">
            <field name="name"/>
            <field name="foo"/>
        </list>
    `;
    Partner._views["search"] = `
        <search>
            <group expand="0" string="Group By">
                <filter name="groupby_bar" context="{'group_by' : 'bar'}"/>
            </group>
        </search>
    `;

    await mountWithCleanup(WebClient);
    getService("dialog").add(SelectCreateDialog, {
        noCreate: true,
        resModel: "partner",
        domain: [["name", "like", "a"]],
        context: {
            search_default_groupby_bar: true,
        },
    });
    await animationFrame();
    await contains("thead .o_list_record_selector input").click();

    await animationFrame();
    expect(".o_select_button:not([disabled])").toHaveCount(1);
});
