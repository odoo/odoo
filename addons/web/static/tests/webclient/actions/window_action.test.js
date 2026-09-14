// @ts-check

import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    clickSave,
    contains,
    createKanbanRecord,
    defineActions,
    defineModels,
    editFavoriteName,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    editSearch,
    fields,
    getPagerLimit,
    getPagerValue,
    getService,
    makeMockEnv,
    makeServerError,
    MockServer,
    models,
    mountWebClient,
    onRpc,
    pagerNext,
    patchWithCleanup,
    removeFacet,
    saveFavorite,
    serverState,
    stepAllNetworkCalls,
    switchView,
    toggleMenuItem,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
    webModels,
} from "@web/../tests/web_test_helpers";
import { useSetupAction } from "@web/core/action_hook";
import { browser } from "@web/core/browser/browser";
import { router, routerBus } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { listView } from "@web/views/list/list_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { clearUncommittedChanges } from "@web/webclient/actions/action_service";

const { ResCompany, ResPartner, ResUsers } = webModels;

function clickListNew() {
    return contains(".o_control_panel_main_buttons .o_list_button_add").click();
}

class Partner extends models.Model {
    _rec_name = "display_name";

    display_name = fields.Char();
    foo = fields.Char();
    m2o = fields.Many2one({ relation: "partner" });
    o2m = fields.One2many({ relation: "partner" });

    _records = [
        { id: 1, display_name: "First record", foo: "yop", m2o: 3, o2m: [2, 3] },
        { id: 2, display_name: "Second record", foo: "blip", m2o: 3, o2m: [1, 4, 5] },
        { id: 3, display_name: "Third record", foo: "gnap", m2o: 1, o2m: [] },
        { id: 4, display_name: "Fourth record", foo: "plop", m2o: 1, o2m: [] },
        { id: 5, display_name: "Fifth record", foo: "zoup", m2o: 1, o2m: [] },
    ];
    _views = {
        "form,3": `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>
        `,
        "form,74": `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" icon="fa-star" context="{'default_partner': id}">
                            <field string="Partners" name="o2m" widget="statinfo"/>
                        </button>
                    </div>
                    <field name="display_name"/>
                </sheet>
            </form>
        `,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `
            <list>
                <field name="foo" />
            </list>
        `,
        search: `
            <search>
                <field name="foo" string="Foo" />
            </search>
        `,
        "search,4": `
            <search>
                <filter name="m2o" help="M2O" domain="[('m2o', '=', 1)]" />
            </search>`,
    };
}

class Pony extends models.Model {
    name = fields.Char();

    _records = [
        { id: 4, name: "Twilight Sparkle" },
        { id: 6, name: "Applejack" },
        { id: 9, name: "Fluttershy" },
    ];
    _views = {
        list: `<list><field name="name"/></list>`,
        form: `<form><field name="name"/></form>`,
    };
}

class Project extends models.Model {
    foo = fields.Boolean({ string: "Foo" });
    _records = [
        {
            id: 1,
            foo: true,
        },
        {
            id: 2,
            foo: false,
        },
    ];

    _views = {
        search: `<search/>`,
        list: `<list><field name="foo"/></list>`,
        kanban: `<kanban><templates><t t-name="card"><field name="foo" /></t></templates></kanban>`,
    };
}

defineModels([Partner, Pony, Project, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[1, "kanban"]],
    },
    {
        id: 2,
        xml_id: "action_2",
        name: "Partner",
        res_id: 2,
        res_model: "partner",
        views: [[74, "form"]],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        views: [
            [1, "kanban"],
            [false, "list"],
            [false, "form"],
        ],
    },
    {
        id: 5,
        xml_id: "action_5",
        name: "Create a Partner",
        res_model: "partner",
        target: "new",
        views: [[false, "form"]],
    },
    {
        id: 8,
        xml_id: "action_8",
        name: "Favorite Ponies",
        res_model: "pony",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    },
    {
        id: 9,
        xml_id: "action_9",
        name: "Ponies",
        res_model: "pony",
        views: [[false, "list"]],
    },
]);

test("can execute act_window actions from db ID", async () => {
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(1);
    expect(".o_control_panel").toHaveCount(1, {
        message: "should have rendered a control panel",
    });
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should have rendered a kanban view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test("click on a list row when there is no form in the action", async () => {
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
    await contains(".o_data_row:eq(0) .o_data_cell").click();
    expect.verifySteps([]);
});

test("click on open form view button when there is no form in the action", async () => {
    Pony._views["list"] =
        `<list editable="top" open_form_view="1"><field name="name"/></list>`;
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
    await contains(".o_data_row:eq(0) .o_list_record_open_form_view").click();
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect.verifySteps(["get_views", "web_read"]);
});

test("click on new record button in list when there is no form in the action", async () => {
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
    await contains(".o_list_button_add").click();
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect.verifySteps(["get_views", "onchange"]);
});

test.tags("desktop");
test("sidebar is present in list view", async () => {
    expect.assertions(4);

    Partner._toolbar = {
        print: [{ name: "Print that record" }],
    };
    onRpc("get_views", ({ kwargs }) => {
        expect(kwargs.options.toolbar).toBe(true, {
            message: "should ask for toolbar information",
        });
    });

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_cp_action_menus .o_dropdown_title").toHaveCount(0);

    await contains("input.form-check-input").click();
    expect('.o_cp_action_menus button.dropdown-toggle:contains("Print")').toBeVisible();
    expect(
        '.o_cp_action_menus button.dropdown-toggle:contains("Action")',
    ).toBeVisible();
});

test.tags("desktop");
test("can switch between views", async () => {
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });

    await switchView("kanban");
    expect(".o_list_view").toHaveCount(0, {
        message: "should no longer display the list view",
    });
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view",
    });

    await switchView("list");
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_kanban_view").toHaveCount(0, {
        message: "should no longer display the kanban view",
    });

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(0, {
        message: "should no longer display the list view",
    });
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "should have opened the correct record",
    });

    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_form_view").toHaveCount(0, {
        message: "should no longer display the form view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_search_read",
        "web_search_read",
        "web_read",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching into a view with mode=edit lands in edit mode", async () => {
    Partner._views["kanban,1"] = `
        <kanban on_create="quick_create" default_group_by="m2o">
            <templates>
                <t t-name="card">
                    <field name="foo"/>
                </t>
            </templates>
        </kanban>`;
    defineActions([
        {
            id: 10,
            xml_id: "action_1",
            name: "Partners Action 1 patched",
            res_model: "partner",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
        },
    ]);
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(10);
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view",
    });
    await createKanbanRecord();
    await editKanbanRecordQuickCreateInput("display_name", "New name");
    await editKanbanRecord();
    expect(".o_form_view .o_form_editable").toHaveCount(1, {
        message: "should display the form view in edit mode",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read_group",
        "onchange",
        "name_create",
        "web_read",
        "web_read",
    ]);
});

test.tags("desktop");
test("orderedBy in context is not propagated when executing another action", async () => {
    expect.assertions(6);

    Partner._views["form"] = `
        <form>
            <header>
                <button name="8" string="Execute action" type="action"/>
            </header>
        </form>`;
    Partner._filters = [
        {
            id: 1,
            context: "{}",
            domain: "[]",
            sort: "[]",
            is_default: true,
            name: "My filter",
            user_ids: [],
        },
    ];

    let searchReadCount = 1;
    onRpc("web_search_read", ({ model, kwargs }) => {
        if (searchReadCount === 1) {
            expect(model).toBe("partner");
            expect(kwargs.sort).toBe(undefined);
        }
        if (searchReadCount === 2) {
            expect(model).toBe("partner");
            expect(kwargs.order).toBe("foo ASC");
        }
        if (searchReadCount === 3) {
            expect(model).toBe("pony");
            expect(kwargs.sort).toBe(undefined);
        }
        searchReadCount += 1;
    });

    await mountWebClient();
    await getService("action").doAction(3);
    await contains(".o_list_view th.o_column_sortable").click();
    await contains(".o_data_cell").click();
    await contains('button[name="8"]').click();
});

test.tags("desktop");
test("breadcrumbs are updated when switching between views", async () => {
    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners");

    await switchView("kanban");
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners");

    await contains(".o_kanban_view .o_kanban_record").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);

    await switchView("list");
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);

    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_list_view").toHaveCount(1, { message: "should be back on list view" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
});

test.tags("desktop");
test("switch buttons are updated when switching between views", async () => {
    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_control_panel button.o_switch_view").toHaveCount(2, {
        message: "should have two switch buttons (list and kanban)",
    });
    expect(".o_control_panel button.o_switch_view.active").toHaveCount(1, {
        message: "should have only one active button",
    });
    expect(".o_control_panel .o_switch_view:first").toHaveClass("o_list", {
        message: "list switch button should be the first one",
    });
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list should be the active view",
    });

    await switchView("kanban");
    expect(".o_control_panel .o_switch_view").toHaveCount(2, {
        message: "should still have two switch buttons (list and kanban)",
    });
    expect(".o_control_panel .o_switch_view.active").toHaveCount(1, {
        message: "should still have only one active button",
    });
    expect(".o_control_panel .o_switch_view:first").toHaveClass("o_list", {
        message: "list switch button should still be the first one",
    });
    expect(".o_control_panel .o_switch_view.o_kanban").toHaveClass("active", {
        message: "kanban should now be the active view",
    });

    await switchView("list");
    expect(".o_control_panel .o_switch_view").toHaveCount(2, {
        message: "should still have two switch buttons (list and kanban)",
    });
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list should now be the active view",
    });

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_control_panel .o_switch_view").toHaveCount(0, {
        message: "should not have any switch buttons",
    });

    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_control_panel .o_switch_view").toHaveCount(2, {
        message: "should have two switch buttons (list and kanban)",
    });
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list should be the active view",
    });
});
test.tags("desktop");
test("pager is updated when switching between views", async () => {
    Partner._views["list"] = `<list limit="3"><field name="foo"/></list>`;

    await mountWebClient();
    await getService("action").doAction(4);
    expect(".o_control_panel .o_pager_value").toHaveText("1-5", {
        message: "value should be correct for kanban",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for kanban",
    });

    await switchView("list");
    expect(".o_control_panel .o_pager_value").toHaveText("1-3", {
        message: "value should be correct for list",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for list",
    });

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_control_panel .o_pager_value").toHaveText("1", {
        message: "value should be correct for form",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("3", {
        message: "limit should be correct for form",
    });

    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_control_panel .o_pager_value").toHaveText("1-3", {
        message: "value should be correct for list",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for list",
    });

    await switchView("kanban");
    expect(".o_control_panel .o_pager_value").toHaveText("1-5", {
        message: "value should be correct for kanban",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for kanban",
    });
});

test.tags("desktop");
test("Props are updated and kept when switching/restoring views", async () => {
    Partner._views["form"] = `
        <form>
            <group>
                <field name="display_name" />
                <field name="m2o" />
            </group>
        </form>`;

    onRpc("get_formview_action", ({ args, model }) => ({
        res_id: args[0][0],
        res_model: model,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    }));

    await mountWebClient();
    await getService("action").doAction(3);

    expect(".o_data_row").toHaveCount(5);

    await contains(".o_data_row:first-of-type .o_data_cell").click();

    expect(".o_field_char input").toHaveValue("First record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(5);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();

    expect(".o_field_char input").toHaveValue("Third record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(1);

    await contains(".o_back_button").click();

    expect(".o_field_char input").toHaveValue("First record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(5);

    await pagerNext();

    expect(".o_field_char input").toHaveValue("Second record");
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(5);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();

    expect(".o_field_char input").toHaveValue("Third record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(1);

    await contains(".o_back_button").click();

    expect(".o_field_char input").toHaveValue("Second record");
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(5);
});

test.tags("desktop");
test("domain is kept when switching between views", async () => {
    defineActions([
        {
            id: 30,
            name: "Partners",
            res_model: "partner",
            search_view_id: [4, "a custom search view"],
            views: [
                [false, "list"],
                [1, "kanban"],
                [false, "form"],
            ],
        },
    ]);

    await mountWebClient();
    await getService("action").doAction(30);
    expect(".o_data_row").toHaveCount(5);

    await toggleSearchBarMenu();
    await toggleMenuItem("M2O");
    expect(".o_data_row").toHaveCount(3);

    await switchView("kanban");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);

    await contains(".o_searchview .o_facet_remove").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);

    await switchView("list");
    expect(".o_data_row").toHaveCount(5);
});

test.tags("desktop");
test("A new form view can be reloaded after a failed one", async () => {
    expect.errors(1);
    await mountWebClient();

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, {
        message: "The list view should be displayed",
    });
    await runAllTimers();
    expect(router.current).toEqual({
        action: 3,
        actionStack: [
            {
                action: 3,
                displayName: "Partners",
                view_type: "list",
            },
        ],
    });

    await contains(".o_list_view .o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, {
        message: "The form view should be displayed",
    });
    expect(".o_last_breadcrumb_item").toHaveText("First record");
    await runAllTimers();
    expect(browser.location.pathname).toBe("/odoo/action-3/1");

    await contains(".o_cp_action_menus .fa-cog").click();
    await contains(".o_menu_item:contains(Delete)").click();
    expect(".modal").toHaveCount(1, { message: "a confirm modal should be displayed" });
    await contains(".modal-footer button.btn-primary").click();
    expect(".o_last_breadcrumb_item").toHaveText("Second record");
    await runAllTimers();
    expect(browser.location.pathname).toBe("/odoo/action-3/2");

    browser.history.back();
    await runAllTimers();
    expect(browser.location.pathname).toBe("/odoo/action-3/1");
    await runAllTimers();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view",
    });
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, {
        message:
            "The form view should still load after a previous failed update | reload",
    });
    expect(".o_last_breadcrumb_item").toHaveText("Second record");

    expect.verifyErrors([
        "It seems the records with IDs 1 cannot be found. They might have been deleted.",
    ]);
});

test.tags("desktop");
test("there is no flickering when switching between views", async () => {
    let def;
    onRpc(() => def);
    Partner._views.list = `<list>
                                <field name="display_name"/>
                                <field name="foo"/>
                            </list>`;

    await mountWebClient();
    await getService("action").doAction(3);

    def = new Deferred();
    await switchView("kanban");
    expect(".o_list_view").toHaveCount(0, {
        message: "shouldn't display the list anymore",
    });
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display an empty kanban",
    });
    expect(".o_kanban_view .o_kanban_record").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, { message: "should display the kanban" });
    expect(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);

    def = new Deferred();
    await switchView("list");
    expect(".o_kanban_view").toHaveCount(0, {
        message: "shouldn't display the kanban anymore",
    });
    expect(".o_list_view").toHaveCount(1, {
        message: "should display an empty list view",
    });
    expect(".o_list_view table").toHaveCount(1);
    expect(".o_list_view table .o_data_row").toHaveCount(5);

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(0, {
        message: "shouldn't display the kanban view anymore",
    });
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_list_view table .o_data_row").toHaveCount(5);

    def = new Deferred();
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view",
    });
    expect(".o_form_view").toHaveCount(0, {
        message: "shouldn't display the form view yet",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);

    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "should no longer display the list view",
    });
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    def = new Deferred();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view").toHaveCount(0, {
        message: "shouldn't display the form anymore",
    });
    expect(".o_list_view").toHaveCount(1, { message: "should display an empty list" });
    expect(".o_list_view table").toHaveCount(1);
    expect(".o_list_view table .o_data_row").toHaveCount(5);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);

    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_list_view table .o_data_row").toHaveCount(5);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
});

test.tags("desktop");
test("there is no flickering when reloading a view", async () => {
    let def;
    onRpc(() => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(5);

    MockServer.env["partner"].create([{ foo: "a new record" }]);
    def = new Deferred();
    await switchView("list");
    expect(".o_list_view .o_data_row").toHaveCount(5);

    def.resolve();
    await animationFrame();
    expect(".o_list_view .o_data_row").toHaveCount(6);

    await switchView("kanban");
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(6);

    MockServer.env["partner"].create([{ foo: "yet another record" }]);
    def = new Deferred();
    await switchView("kanban");
    expect(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(6);

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(7);
});

test.tags("desktop");
test("breadcrumbs are updated when display_name changes", async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    await contains(".o_field_widget[name=display_name] input").edit("New name");
    await clickSave();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "New name",
    ]);
});

test.tags("desktop");
test('reverse breadcrumb works on accesskey "b"', async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    await contains(".o_form_view button:contains(Execute action)").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);
    expect(".breadcrumb-item.o_back_button").toHaveAttribute("data-hotkey", "b", {
        message: "previous breadcrumb should have accessKey 'b'",
    });

    await contains(".breadcrumb-item.o_back_button").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);
    expect(".breadcrumb-item.o_back_button").toHaveAttribute("data-hotkey", "b", {
        message: "previous breadcrumb should have accessKey 'b'",
    });
});

test.tags("desktop");
test("reload previous controller when discarding a new record", async () => {
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(3);

    await clickListNew();
    expect(".o_form_view .o_form_editable").toHaveCount(1, {
        message: "should have opened the form view in edit mode",
    });

    await contains(".o_control_panel .o_form_button_cancel").click();
    expect(".o_list_view").toHaveCount(1, {
        message: "should have switched back to the list view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "onchange",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("execute_action of type object are handled", async () => {
    expect.assertions(4);
    serverState.userContext = { some_key: 2 };

    onRpc("partner", "object", function ({ args, kwargs }) {
        expect(kwargs).toMatchObject(
            {
                context: { some_key: 2 },
            },
            { message: "should call route with correct arguments" },
        );
        return this.env["partner"].write(args[0], { foo: "value changed" });
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "check initial value of 'yop' field",
    });

    await contains(".o_form_view button:contains(Call method)").click();
    expect(".o_field_widget[name=foo] input").toHaveValue("value changed", {
        message:
            "'yop' has been changed by the server, and should be updated in the UI",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "object",
        "web_read",
    ]);
});

test.tags("desktop");
test("execute_action of type object: disable buttons (2)", async () => {
    Partner._views["form"] = `
        <form>
            <header>
                <button name="object" string="Call method" type="object"/>
                <button name="40" string="Execute action" type="action"/>
            </header>
            <group>
                <field name="display_name"/>
                <field name="foo"/>
            </group>
        </form>`;
    Pony._views["form,44"] = `
        <form>
            <field name="name"/>
            <button string="Cancel" class="cancel-btn" special="cancel"/>
        </form>`;

    defineActions([
        {
            id: 40,
            name: "Create a Partner",
            res_model: "pony",
            target: "new",
            views: [[44, "form"]],
        },
    ]);

    const def = new Deferred();
    onRpc("onchange", () => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains('.o_form_view button[name="40"]').click();
    expect(".o_form_button_create").not.toBeEnabled();

    def.resolve();
    await animationFrame();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".o_form_button_create").toBeEnabled();

    await contains(".modal .cancel-btn").click();
    expect(".o_form_button_create").toBeEnabled();
});

test.tags("desktop");
test("view button: block ui attribute", async () => {
    Partner._views["form"] = `
            <form>
                <header>
                    <button name="4" string="Execute action" type="action" block-ui="1"/>
                </header>
            </form>`;

    const def = new Deferred();
    onRpc("onchange", () => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o-main-components-container .o_blockUI").toHaveCount(0);

    await contains('.o_form_view button[name="4"]').click();
    expect(".o-main-components-container .o_blockUI").toHaveCount(1, {
        message: "interface should be blocked during loading",
    });

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o-main-components-container .o_blockUI").toHaveCount(0);
});

test.tags("desktop");
test("execute_action of type object raises error: re-enables buttons", async () => {
    expect.errors(1);

    onRpc("/web/dataset/call_button/*", () => {
        throw makeServerError({ message: "This is a user error" });
    });

    await mountWebClient();
    await getService("action").doAction(3, { viewType: "form" });
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_form_button_save").click();

    await click('.o_form_view button[name="object"]');
    expect(".o_form_button_create").not.toBeEnabled();
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_form_button_create").toBeEnabled();
});

test("execute_action of type object raises error in modal: re-enables buttons", async () => {
    expect.errors(1);
    Partner._views["form"] = `
            <form>
                <field name="display_name"/>
                <footer>
                    <button name="object" string="Call method" type="object"/>
                </footer>
            </form>`;

    onRpc("/web/dataset/call_button/*", () => {
        throw makeServerError();
    });

    await mountWebClient();
    await getService("action").doAction(5);
    expect(".modal .o_form_view").toHaveCount(1);
    await click('.modal footer button[name="object"]');
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal footer button").not.toBeEnabled();
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal footer button").toBeEnabled();
});

test.tags("desktop");
test("execute_action of type action are handled", async () => {
    stepAllNetworkCalls();
    await mountWebClient();
    await getService("action").doAction(3);
    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);
    await contains(".o_form_view button:contains(Execute action)").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);
    expect(".o_kanban_view").toHaveCount(1, {
        message: "the returned action should have been executed",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("mobile");
test("smart button runs even when the tap lands on the More item wrapper", async () => {
    await mountWebClient();
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    await contains(".o-form-buttonbox .o_button_more").click();
    await animationFrame();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(1);
    await contains(".o_bottom_sheet .o-dropdown-item").click();
    await animationFrame();
    await runAllTimers();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
});

test.tags("desktop");
test("execute smart button and back", async () => {
    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.context).not.toInclude("default_partner");
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.context.default_partner).toBe(2);
    });

    await mountWebClient();
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);

    await contains(".oe_stat_button").click();
    expect(".o_kanban_view").toHaveCount(1);

    await contains(".breadcrumb-item").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);
    expect.verifySteps(["web_read", "web_search_read", "web_read"]);
});

test.tags("desktop");
test("execute smart button and fails on desktop", async () => {
    expect.errors(1);
    const def = new Deferred();
    onRpc("web_search_read", async () => {
        await def;
        throw makeServerError({ message: "Oups" });
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);

    await contains("button.oe_stat_button").click();
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);

    def.resolve();
    await waitFor(".o_form_view");
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
    ]);
    await expect.waitForErrors(["Oups"]);
});

test.tags("mobile");
test("execute smart button and fails on mobile", async () => {
    expect.errors(1);
    const def = new Deferred();
    onRpc("web_search_read", async () => {
        await def;
        throw makeServerError({ message: "Oups" });
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);

    await contains(".o-form-buttonbox .o_button_more").click();
    await contains("button.oe_stat_button").click();
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);

    def.resolve();
    await waitFor(".o_form_view");
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
    ]);
    await expect.waitForErrors(["Oups"]);
});

test.tags("desktop");
test("requests for execute_action of type object: disable buttons", async () => {
    let def = undefined;
    onRpc("web_read", () => def);
    onRpc("/web/dataset/call_button/*", () => false);

    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();

    def = new Deferred();
    await contains(".o_form_view button:contains(Call method)").click();

    expect(".o_form_view button:contains(Call method)").not.toBeEnabled();

    def.resolve();
    await animationFrame();

    expect(".o_form_view button:contains(Call method)").toBeEnabled();
});

test.tags("desktop");
test("action with html help returned by a call_button", async () => {
    onRpc("/web/dataset/call_button/*", () => ({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
        help: "<p>I am not a helper</p>",
        domain: [[0, "=", 1]],
    }));

    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await contains(".o_statusbar_buttons button").click();
    expect(".o_list_view .o_nocontent_help p").toHaveText("I am not a helper");
});

test.tags("desktop");
test("can open different records from a multi record view", async () => {
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_breadcrumb .active").toHaveText("First record", {
        message: "breadcrumbs should contain the display_name of the opened record",
    });
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "should have opened the correct record",
    });

    await contains(".o_control_panel .breadcrumb a").click();

    await contains(".o_list_view .o_data_row:eq(1) .o_data_cell:first").click();
    expect(".o_breadcrumb .active").toHaveText("Second record", {
        message: "breadcrumbs should contain the display_name of the opened record",
    });
    expect(".o_field_widget[name=foo] input").toHaveValue("blip", {
        message: "should have opened the correct record",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "web_search_read",
        "web_read",
    ]);
});

test.tags("desktop");
test("restore previous view state when switching back", async () => {
    defineActions([
        {
            id: 30,
            name: "Partners",
            res_model: "partner",
            views: [
                [false, "graph"],
                [1, "kanban"],
                [false, "form"],
            ],
        },
    ]);

    await mountWebClient();
    await getService("action").doAction(30);
    expect(".o_graph_renderer [data-mode='bar']").toHaveClass("active");
    expect(".o_graph_renderer [data-mode='line']").not.toHaveClass("active");

    await contains(".o_graph_renderer [data-mode='line']").click();
    expect(".o_graph_renderer [data-mode='line']").toHaveClass("active");

    await switchView("kanban");
    expect(".o_graph_renderer [data-mode='line']").toHaveCount(0);

    await switchView("graph");
    expect(".o_graph_renderer [data-mode='line']").toHaveClass("active");
});

test.tags("desktop");
test("can't restore previous action if form is invalid", async () => {
    Partner._fields.foo = fields.Char({ required: true });

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=foo]").toHaveClass("o_required_modifier");

    await contains(".o_field_widget[name=display_name] input").edit(
        "make record dirty",
    );
    await contains(".breadcrumb .o_back_button").click();
    expect(".o_list_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_notification_manager .o_notification").toHaveCount(1);
    expect(".o_field_widget[name=foo]").toHaveClass("o_field_invalid");
});

test.tags("desktop");
test("view switcher is properly highlighted in pivot view", async () => {
    defineActions([
        {
            id: 30,
            name: "Partners",
            res_model: "partner",
            views: [
                [false, "list"],
                [false, "pivot"],
                [false, "form"],
            ],
        },
    ]);

    await mountWebClient();
    await getService("action").doAction(30);
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list button in control panel is active",
    });
    expect(".o_control_panel .o_switch_view.o_pivot").not.toHaveClass("active", {
        message: "pivot button in control panel is not active",
    });

    await switchView("pivot");
    expect(".o_control_panel .o_switch_view.o_list").not.toHaveClass("active", {
        message: "list button in control panel is not active",
    });
    expect(".o_control_panel .o_switch_view.o_pivot").toHaveClass("active", {
        message: "pivot button in control panel is active",
    });
});

test.tags("desktop");
test("can interact with search view", async () => {
    Partner._views["search"] = `
        <search>
            <group>
            <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_table").not.toHaveClass("o_list_table_grouped", {
        message: "list view is not grouped",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("foo");
    expect(".o_list_table").toHaveClass("o_list_table_grouped", {
        message: "list view is now grouped",
    });
});

test.tags("desktop");
test("can open a many2one external window", async () => {
    Partner._views["search"] = `
        <search>
            <group>
                <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;
    Partner._views["form"] = `
        <form>
            <field name="foo"/>
            <field name="m2o"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("get_formview_action", () => ({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        res_id: 3,
        views: [[false, "form"]],
    }));
    await mountWebClient();
    await getService("action").doAction(3);
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_external_button", { visible: false }).click();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "get_formview_action",
        "get_views",
        "web_read",
    ]);
});

test.tags("desktop");
test('save when leaving a "dirty" view', async () => {
    expect.assertions(4);
    onRpc("partner", "web_save", ({ args }) => {
        expect(args).toEqual([[1], { foo: "pinkypie" }]);
    });

    await mountWebClient();
    await getService("action").doAction(4);
    await contains(".o_kanban_record").click();
    await contains('.o_field_widget[name="foo"] input').edit("pinkypie");
    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(".modal").toHaveCount(0, { message: "should not display a modal dialog" });
    expect(".o_form_view").toHaveCount(0, {
        message: "should no longer be in form view",
    });
    expect(".o_kanban_view").toHaveCount(1, { message: "should be in kanban view" });
});

test.tags("desktop");
test("limit set in action is passed to each created controller", async () => {
    await mountWebClient();
    await getService("action").doAction({
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        limit: 2,
        views: [
            [false, "list"],
            [false, "kanban"],
        ],
    });
    expect(".o_data_row").toHaveCount(2);

    await switchView("kanban");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
});

test.tags("desktop");
test("go back to a previous action using the breadcrumbs", async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    await getService("action").doAction(4);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);

    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    await getService("action").doAction(4);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);

    await contains(".o_control_panel .breadcrumb a:first").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
});

test.tags("desktop");
test("form views are restored in edit when coming back in breadcrumbs", async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await getService("action").doAction(4);

    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
});

test.tags("desktop");
test("form views restore the correct id in url when coming back in breadcrumbs", async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await runAllTimers();
    expect(router.current.resId).toBe(1);

    await getService("action").doAction(4);
    await runAllTimers();
    expect(router.current).not.toInclude("resId");

    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    await runAllTimers();
    expect(router.current.resId).toBe(1);
});

test.tags("desktop");
test("honor group_by specified in actions context", async () => {
    defineActions([
        {
            id: 30,
            name: "Partners",
            res_model: "partner",
            context: "{'group_by': 'm2o'}",
            views: [[false, "list"]],
        },
    ]);
    Partner._views["search"] = `
        <search>
            <group>
            <filter name="foo" string="Foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;

    await mountWebClient();
    await getService("action").doAction(30);
    expect(".o_list_table_grouped").toHaveCount(1, { message: "should be grouped" });
    expect(".o_group_header").toHaveCount(2, {
        message: "should be grouped by 'bar' (two groups) at first load",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(".o_group_header").toHaveCount(5, {
        message: "should be grouped by 'foo' (five groups)",
    });

    await contains(".o_control_panel .o_searchview .o_facet_remove").click();
    expect(".o_list_table_grouped").toHaveCount(1, {
        message: "should still be grouped",
    });
    expect(".o_group_header").toHaveCount(2, {
        message: "should be grouped by 'bar' (two groups) at reload",
    });
});

test.tags("desktop");
test("switch request to unknown view type", async () => {
    defineActions(
        [
            {
                id: 33,
                name: "Partners",
                res_model: "partner",
                views: [
                    [false, "list"],
                    [1, "kanban"],
                ],
            },
        ],
        { mode: "replace" },
    );

    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(33);
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    contains(".o_list_view .o_data_row:first").click();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view",
    });
    expect(".o_form_view").toHaveCount(0, {
        message: "should not display the form view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("execute action with unknown view type", async () => {
    defineActions([
        {
            id: 33,
            name: "Partners",
            res_model: "partner",
            views: [
                [false, "list"],
                [false, "unknown"],
                [false, "kanban"],
                [false, "form"],
            ],
        },
    ]);
    await mountWebClient();
    await expect(getService("action").doAction(33)).rejects.toThrow(
        /View types not defined unknown found in act_window action 33/,
    );
});

test.tags("desktop");
test("save current search", async () => {
    expect.assertions(4);

    defineActions([
        {
            id: 33,
            context: {
                shouldNotBeInFilterContext: false,
            },
            name: "Partners",
            res_model: "partner",
            search_view_id: [4, "a custom search view"],
            views: [[false, "list"]],
        },
    ]);
    patchWithCleanup(listView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            useSetupAction({
                getContext: () => ({ shouldBeInFilterContext: true }),
            });
        },
    });

    onRpc("create_filter", ({ args }) => {
        expect(args[0].domain).toBe(`[("m2o", "=", 1)]`);
        expect(args[0].context).toEqual({
            group_by: [],
            shouldBeInFilterContext: true,
        });
        return [3];
    });

    await mountWebClient();
    await getService("action").doAction(33);
    expect(".o_data_row").toHaveCount(5, { message: "should contain 5 records" });

    await toggleSearchBarMenu();
    await toggleMenuItem("M2O");
    expect(".o_data_row").toHaveCount(3);

    await toggleSaveFavorite();
    await editFavoriteName("some name");
    await saveFavorite();
});

test.tags("desktop");
test("list with default_order and favorite filter with no orderedBy", async () => {
    Partner._views["list,1"] =
        '<list default_order="foo desc"><field name="foo"/></list>';
    defineActions([
        {
            id: 100,
            name: "Partners",
            res_model: "partner",
            views: [
                [1, "list"],
                [false, "form"],
            ],
        },
    ]);
    Partner._filters = [
        {
            name: "favorite filter",
            id: 5,
            context: "{}",
            sort: "[]",
            domain: '[("m2o", "=", 1)]',
            is_default: false,
            user_ids: [],
        },
    ];
    await mountWebClient();
    await getService("action").doAction(100);
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "yop", "plop", "gnap", "blip"],
        { message: "record should be in descending order as default_order applies" },
    );

    await toggleSearchBarMenu();
    await toggleMenuItem("favorite filter");
    expect(".o_control_panel .o_facet_values").toHaveText("favorite filter", {
        message: "favorite filter should be applied",
    });
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "plop", "gnap"],
        {
            message:
                "record should still be in descending order after default_order applied",
        },
    );

    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "plop", "gnap"],
        {
            message:
                "order of records should not be changed, while coming back through breadcrumb",
        },
    );

    await removeFacet("favorite filter");
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "yop", "plop", "gnap", "blip"],
        {
            message:
                "order of records should not be changed, after removing current filter",
        },
    );
});

test.tags("desktop");
test("action with default favorite and context.active_id", async () => {
    expect.assertions(4);

    defineActions([
        {
            id: 30,
            name: "Partners",
            res_model: "partner",
            context:
                "{ 'active_id': 4, 'active_ids': [4], 'active_model': 'whatever' }",
            views: [[false, "list"]],
        },
    ]);
    Partner._filters = [
        {
            name: "favorite filter",
            id: 5,
            context: "{}",
            sort: "[]",
            domain: '[("bar", "=", 1)]',
            is_default: true,
            user_ids: [],
        },
    ];
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["bar", "=", 1]]);
    });

    await mountWebClient();
    await getService("action").doAction(30);

    expect(".o_list_view").toHaveCount(1);
    expect(".o_searchview .o_searchview_facet").toHaveCount(1);
    expect(".o_facet_value").toHaveText("favorite filter");
});

test.tags("desktop");
test("search menus are still available when switching between actions", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
    ]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);

    await getService("action").doAction(3);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
        "Partners",
    ]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);

    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
    ]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);
});

test.tags("desktop");
test("current act_window action is stored in session_storage if possible", async () => {
    /** @type {any} */
    let expectedAction = { target: "current", tag: "menu", type: "ir.actions.client" };
    patchWithCleanup(browser.sessionStorage, {
        setItem(key, value) {
            if (key === "current_action") {
                expect(JSON.parse(value)).toEqual(expectedAction);
            }
        },
    });
    await mountWebClient();

    expectedAction = await MockServer.current.loadAction(
        new Request(`${browser.location.origin}/web/action/load`, {
            method: "POST",
            body: JSON.stringify({ params: { action_id: 3 } }),
        }),
    );
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    expectedAction = {};
    const x = {};
    x.y = x;
    await getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "partner",
        views: [[false, "kanban"]],
        flags: { x },
    });
    expect(".o_kanban_view").toHaveCount(1);
});

test("stored action is restored correctly with domain", async () => {
    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        type: "ir.actions.act_window",
        res_model: "partner",
        views: [[false, "list"]],
        view_mode: "list",
        target: "current",
        domain: [["id", "=", 4]],
    });
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(1);

    routerBus.trigger("ROUTE_CHANGE");
    await animationFrame();

    expect(".o_list_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(1);
});

test("current_action doesn't contains _originalAction", async () => {
    class myActionComponent extends Component {
        static template = xml`<div>This is a Client Action</div>`;
        static props = ["*"];
    }

    const myAction = (env, action) => {
        registry
            .category("actions")
            .add("myAction", myActionComponent, { force: true });
        return action;
    };
    registry.category("actions").add("myAction", myAction);
    redirect("/odoo/myAction");
    await mountWebClient();

    await animationFrame();
    expect(JSON.parse(browser.sessionStorage.getItem("current_action"))).toEqual(
        {
            context: {},
            domain: [],
            jsId: "action_1",
            params: {
                action: "myAction",
                actionStack: [
                    {
                        action: "myAction",
                    },
                ],
            },
            tag: "myAction",
            target: "current",
            type: "ir.actions.client",
        },
        { message: "current_action doesn't contains _originalAction" },
    );
});

test.tags("desktop");
test("destroy action with lazy loaded controller", async () => {
    redirect("/odoo/action-3/2");

    await mountWebClient();
    await animationFrame();
    expect(".o_list_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "Second record",
    ]);

    await getService("action").doAction(1, { clearBreadcrumbs: true });
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
});

test.tags("desktop");
test("execute action from dirty, new record, and come back", async () => {
    Partner._fields.bar = fields.Many2one({ relation: "partner", default: 1 });
    Partner._views["form"] = `
        <form>
            <field name="display_name"/>
            <field name="foo"/>
            <field name="bar" readonly="1"/>
        </form>`;

    onRpc("get_formview_action", () => ({
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    }));
    stepAllNetworkCalls();

    await mountWebClient();

    await getService("action").doAction(3);
    await clickListNew();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_form_uri:contains(First record)").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "New",
    ]);

    await contains('.o_field_widget[name="display_name"] input').edit("test");
    await contains(".o_field_widget[name=foo] input").edit("val");
    await contains(".o_form_uri").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "test",
        "First record",
    ]);
    await contains(".o_control_panel .breadcrumb-item a:eq(1)").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "test",
    ]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "onchange",
        "get_formview_action",
        "web_save",
        "get_views",
        "web_read",
        "web_read",
    ]);
});

test.tags("desktop");
test("execute a contextual action from a form view", async () => {
    expect.assertions(4);

    const contextualAction = {
        id: 80,
        name: "Favorite Ponies",
        res_model: "pony",
        context: "{}",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    };
    defineActions([contextualAction]);
    Partner._toolbar = {
        action: [contextualAction],
        print: [],
    };

    onRpc("partner", "get_views", ({ kwargs }) => {
        expect(kwargs.options.toolbar).toBe(true, {
            message: "should ask for toolbar information",
        });
    });

    await mountWebClient();

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_cp_action_menus .fa-cog").click();
    await toggleMenuItem("Favorite Ponies");
    expect(".o_list_view").toHaveCount(1);
});

test.tags("desktop");
test("go back to action with form view as main view, and res_id", async () => {
    defineActions([
        {
            id: 999,
            name: "Partner",
            res_model: "partner",
            res_id: 2,
            views: [[44, "form"]],
        },
    ]);
    Partner._views["form,44"] = '<form><field name="m2o"/></form>';

    onRpc("get_formview_action", () => ({
        res_id: 3,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    }));

    await mountWebClient();
    await getService("action").doAction(999);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
    ]);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
        "Third record",
    ]);

    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
    ]);
});

test.tags("desktop");
test("action with res_id, load another res_id, do new action, restore previous", async () => {
    const action = {
        id: 999,
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        res_id: 1,
        views: [[44, "form"]],
    };
    defineActions([action]);

    Partner._views["form,44"] = '<form><field name="m2o"/></form>';
    onRpc("get_formview_action", () => ({ ...action, res_id: 3 }));

    await mountWebClient();
    await getService("action").doAction(999, { props: { resIds: [1, 2] } });
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "First record",
    ]);
    expect(".o_control_panel .o_pager_counter").toHaveText("1 / 2");

    await contains(".o_pager_next").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
    ]);
    expect(".o_control_panel .o_pager_counter").toHaveText("2 / 2");

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
        "Third record",
    ]);

    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
    ]);
    expect(".o_control_panel .o_pager_counter").toHaveText("2 / 2");
});

test.tags("desktop");
test("open a record, come back, and create a new record", async () => {
    await mountWebClient();

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(5);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(".o_list_view").toHaveCount(1);

    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
});

test.tags("desktop");
test("open form view, use the pager, execute action, and come back", async () => {
    await mountWebClient();

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(5);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("First record");

    await contains(".o_pager_next").click();
    expect(".o_field_widget[name=display_name] input").toHaveValue("Second record");

    await contains(".o_statusbar_buttons button[name='4']").click();
    expect(".o_kanban_view").toHaveCount(1);

    await contains(".o_control_panel .breadcrumb-item:eq(1) a").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("Second record");
});

test.tags("desktop");
test("create a new record in a form view, execute action, and come back", async () => {
    await mountWebClient();

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_field_widget[name=display_name] input").edit("another record");
    await contains(".o_form_button_save").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_statusbar_buttons button[name='4']").click();
    expect(".o_kanban_view").toHaveCount(1);

    await contains(".o_control_panel .breadcrumb-item:eq(1) a").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("another record");
});

test("onClose should be called only once with right parameters", async () => {
    expect.assertions(4);

    await mountWebClient();
    await getService("action").doAction(2);
    await getService("action").doAction(5, {
        onClose(infos) {
            expect.step("onClose");
            expect(infos).toEqual({ cantaloupe: "island" });
        },
    });
    expect(".modal").toHaveCount(1);

    await getService("action").doAction({
        type: "ir.actions.act_window_close",
        infos: { cantaloupe: "island" },
    });
    expect.verifySteps(["onClose"]);
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test.tags("desktop");
test("search view should keep focus during do_search", async () => {
    const searchPromise = new Deferred();
    onRpc("web_search_read", async ({ kwargs }) => {
        expect.step("search_read " + kwargs.domain);
        if (JSON.stringify(kwargs.domain) === JSON.stringify([["foo", "ilike", "m"]])) {
            await searchPromise;
        }
    });

    await mountWebClient();
    await getService("action").doAction(3);
    await editSearch("m");
    await validateSearch();
    expect.verifySteps(["search_read ", "search_read foo,ilike,m"]);

    await editSearch("o");
    searchPromise.resolve();
    await validateSearch();
    expect.verifySteps(["search_read |,foo,ilike,m,foo,ilike,o"]);
});

test.tags("desktop");
test("Call twice clearUncommittedChanges in a row does not save twice", async () => {
    let writeCalls = 0;
    onRpc("web_save", () => {
        writeCalls += 1;
    });

    const env = await makeMockEnv();
    await mountWebClient({ env });

    await getService("action").doAction(3);
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_field_widget[name=foo] input").edit("val");
    clearUncommittedChanges(env);

    await animationFrame();
    expect(".modal").toHaveCount(0);
    clearUncommittedChanges(env);

    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(writeCalls).toBe(1);
});

test.tags("desktop");
test("executing a window action with onchange warning does not hide it", async () => {
    Partner._views["form"] = `<form><field name="foo"/></form>`;

    onRpc("onchange", () => ({
        value: {},
        warning: {
            title: "Warning",
            message: "Everything is alright",
            type: "dialog",
        },
    }));

    await mountWebClient();
    await getService("action").doAction(3);
    await clickListNew();
    await waitFor(".modal.o_technical_modal");
    expect(".modal.o_technical_modal").toHaveCount(1, {
        message: "Warning modal should be opened",
    });

    await contains(".modal.o_technical_modal button.btn-primary").click();
    expect(".modal.o_technical_modal").toHaveCount(0, {
        message: "Warning modal should be closed",
    });
});

test("do not call clearUncommittedChanges() when target=new and dialog is opened", async () => {
    await mountWebClient();

    await getService("action").doAction(3, { viewType: "form" });
    expect(".o_action_manager .o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_field_widget[name=display_name] input").edit("TEST");
    await getService("action").doAction(5);
    expect(".o_action_manager .o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_dialog .o_view_controller").toHaveCount(1);
});

test("do not pushState when target=new and dialog is opened", async () => {
    await mountWebClient();

    await getService("action").doAction(3, { viewType: "form" });
    await runAllTimers();
    const prevUrlState = Object.assign({}, router.current);
    await getService("action").doAction({
        name: "Edit a Partner",
        res_model: "partner",
        res_id: 3,
        type: "ir.actions.act_window",
        views: [[3, "form"]],
        target: "new",
        view_mode: "form",
    });
    await runAllTimers();
    expect(router.current).toEqual(prevUrlState, {
        message: "push_state in dialog shouldn't change the hash",
    });
});

test("do not restore after action button clicked", async () => {
    Partner._views.form = `
        <form>
            <header>
                <button name="do_something" string="Call button" type="object"/>
            </header>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>`;

    onRpc("/web/dataset/call_button/*", () => true);

    await mountWebClient();
    await getService("action").doAction(3, { viewType: "form", props: { resId: 1 } });
    await contains("div[name='display_name'] input").edit("Edited value");
    expect(".o_form_button_save").toBeVisible();
    expect(".o_statusbar_buttons button[name=do_something]").toBeVisible();

    await contains(".o_statusbar_buttons button[name=do_something]").click();
    expect(".o_control_panel_main_buttons .o_form_button_save").not.toHaveCount();
});

test("debugManager is active for views", async () => {
    serverState.debug = "1";
    onRpc("has_access", () => true);
    await mountWebClient();
    await getService("action").doAction(1);
    expect(".o-dropdown--menu .o-dropdown-item:contains('View: Kanban')").toHaveCount(
        0,
    );
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".o-dropdown--menu .o-dropdown-item:contains('View: Kanban')").toHaveCount(
        1,
    );
});

test.tags("desktop");
test("reload a view via the view switcher keep state", async () => {
    onRpc("formatted_read_grouping_sets", () => {
        expect.step("formatted_read_grouping_sets");
    });

    await mountWebClient();
    await getService("action").doAction({
        id: 3,
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "pivot"],
            [false, "list"],
        ],
    });
    expect(".o_pivot_measure_row").not.toHaveClass("o_pivot_sort_order_asc");

    await contains(".o_pivot_measure_row").click();
    expect(".o_pivot_measure_row").toHaveClass("o_pivot_sort_order_asc");

    await switchView("pivot");
    expect(".o_pivot_measure_row").toHaveClass("o_pivot_sort_order_asc");
    expect.verifySteps([
        "formatted_read_grouping_sets",
        "formatted_read_grouping_sets",
    ]);
});

test("doAction supports being passed globalState prop", async () => {
    expect.assertions(1);

    const searchModel = JSON.stringify({
        nextGroupId: 2,
        nextGroupNumber: 2,
        nextId: 2,
        searchItems: {
            1: {
                description: `ID is "99"`,
                domain: `[("id","=",99)]`,
                type: "filter",
                groupId: 1,
                groupNumber: 1,
                id: 1,
            },
        },
        query: [{ searchItemId: 1 }],
        sections: [],
    });

    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["id", "=", 99]]);
    });

    await mountWebClient();
    await getService("action").doAction(1, {
        props: {
            globalState: { searchModel },
        },
    });
});

test("window action in target new fails (onchange)", async () => {
    expect.errors(1);

    onRpc("partner", "onchange", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = `
        <form>
            <header>
                <button name="5" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWebClient();
    await getService("action").doAction(2);
    await contains(".o_form_view button[name='5']").click();
    await expect(waitFor(".modal .o_error_dialog .modal-title")).resolves.toHaveText(
        "Validation Error",
    );
    expect.verifyErrors(["RPC_ERROR"]);
});

test("Uncaught error in target new is catch only once", async () => {
    expect.errors(1);

    defineActions([
        {
            id: 26,
            name: "Partner",
            res_model: "partner",
            target: "new",
            views: [[false, "list"]],
        },
    ]);

    onRpc("partner", "web_search_read", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = `
        <form>
            <header>
                <button name="26" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWebClient();
    await getService("action").doAction(2);
    await contains(".o_form_view button[name='26']").click();
    await expect(waitFor(".modal .o_error_dialog .modal-title")).resolves.toHaveText(
        "Validation Error",
    );
    expect.verifyErrors(["RPC_ERROR"]);
});

test("action and get_views rpcs are cached", async () => {
    class IrActionsAct_Window extends models.Model {
        _name = "ir.actions.act_window";
    }
    defineModels([IrActionsAct_Window]);

    stepAllNetworkCalls();

    await mountWebClient();
    expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);

    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    expect.verifySteps(["web_search_read"]);

    await getService("orm").unlink("ir.actions.act_window", [333]);
    await animationFrame();
    expect.verifySteps(["unlink", "/web/action/load_breadcrumbs"]);
    await getService("action").doAction(1);
    expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
});

test("get_views rpcs are cached (different context.active_id)", async () => {
    class IrActionsAct_Window extends models.Model {
        _name = "ir.actions.act_window";
    }
    defineModels([IrActionsAct_Window]);

    stepAllNetworkCalls();

    await mountWebClient();
    expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: { active_id: 33 },
    });
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["get_views", "web_search_read"]);

    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        context: { active_id: 44 },
    });
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["web_search_read"]);
});

test.tags("desktop");
test("pushState also changes the title of the tab", async () => {
    await mountWebClient();
    await getService("action").doAction(3);

    const titleService = getService("title");
    expect(titleService.current).toBe("Partners");

    await contains(".o_data_row .o_data_cell").click();
    expect(titleService.current).toBe("First record");

    await contains(".o_pager_next").click();
    expect(titleService.current).toBe("Second record");
});

test("action group_by of type string", async () => {
    Partner._views["pivot,3"] = `<pivot />`;
    await mountWebClient();
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[3, "pivot"]],
        context: { group_by: "foo" },
    });
    expect(".o_pivot_view").toHaveCount(1);
    expect(".o_pivot_view tbody th").toHaveCount(6);
});

test("action help given to View in props if not empty", async () => {
    Partner._records = [];

    const action = {
        name: "Partners",
        res_model: "partner",
        views: [[false, "list"]],
    };
    defineActions([
        {
            ...action,
            id: 14,
            help: '<p class="hello">Hello</p>',
        },
        {
            ...action,
            id: 15,
            help: '<p class="hello"></p>',
        },
    ]);

    await mountWebClient();
    await getService("action").doAction(14);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_view_nocontent").toHaveText("Hello");
    expect("table").toHaveCount(1);

    await getService("action").doAction(15);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
});

test("load a tree", async () => {
    Partner._views = {
        list: `<list><field name="foo"/></list>`,
    };

    await mountWebClient();
    await getService("action").doAction({
        res_id: 1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "partner",
        views: [[false, "list"]],
    });
    expect(".o_list_view").toHaveCount(1);
});

test.tags("desktop");
test("sample server: populate groups", async () => {
    Partner._records = [];
    Partner._views = {
        kanban: `
            <kanban sample="1" default_group_by="write_date:month">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        pivot: `
            <pivot sample="1">
                <field name="write_date" type="row"/>
            </pivot>`,
    };
    onRpc("web_read_group", () => ({
        groups: [
            {
                __count: 0,
                "write_date:month": ["2022-12-01", "December 2022"],
                __extra_domain: [
                    ["write_date", ">=", "2022-12-01"],
                    ["write_date", "<", "2023-01-01"],
                ],
            },
        ],
        length: 1,
    }));

    await mountWebClient();
    await getService("action").doAction({
        res_id: 1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "partner",
        views: [
            [false, "kanban"],
            [false, "pivot"],
        ],
    });

    expect(".o_kanban_view .o_view_sample_data").toHaveCount(1);
    expect(".o_column_title").toHaveText("December 2022");

    await switchView("pivot");
    expect(".o_pivot_view .o_view_sample_data").toHaveCount(1);
});

test.tags("desktop");
test("click on breadcrumb of a deleted record", async () => {
    expect.errors(1);
    Partner._views["form"] = `
        <form>
            <button type="action" name="3" string="Open Action 3" class="my_btn"/>
        </form>`;

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".my_btn").click();
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item")).toEqual(["", "First record", "Partners"]);
    expect(".o_breadcrumb .active").toHaveText("First record");
    await contains(".o_cp_action_menus .fa-cog").click();
    await toggleMenuItem("Delete");
    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog .modal-footer .btn-primary").click();

    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item")).toEqual(["", "First record", "Partners"]);
    expect(".o_breadcrumb .active").toHaveText("Second record");

    await contains(".breadcrumb-item a").click();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item")).toEqual([]);
    expect(".o_breadcrumb .active").toHaveText("Partners");
    expect.verifyErrors([
        "It seems the records with IDs 1 cannot be found. They might have been deleted.",
    ]);
});

test.tags("desktop");
test("executing an action closes dialogs", async () => {
    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    getService("dialog").add(FormViewDialog, { resModel: "partner", resId: 1 });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);

    await contains(
        ".o_dialog .o_form_view .o_statusbar_buttons button[name='4']",
    ).click();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_dialog").toHaveCount(0);
});

test.tags("mobile");
test("execute a window action with mobile_view_mode", async () => {
    await mountWebClient();
    await getService("action").doAction({
        xml_id: "project.action",
        name: "Project Action",
        res_model: "project",
        type: "ir.actions.act_window",
        view_mode: "list,kanban",
        mobile_view_mode: "list",
        views: [
            [false, "kanban"],
            [false, "list"],
        ],
    });
    expect(".o_list_view").toHaveCount(1);
});
