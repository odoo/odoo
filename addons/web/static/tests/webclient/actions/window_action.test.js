import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    MockServer,
    contains,
    createKanbanRecord,
    defineActions,
    defineModels,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    stepAllNetworkCalls,
    switchView,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { redirect } from "@web/core/utils/urls";
import { useSetupAction } from "@web/search/action_hook";
import { listView } from "@web/views/list/list_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { clearUncommittedChanges } from "@web/webclient/actions/action_service";
import { WebClient } from "@web/webclient/webclient";
import {
    clickSave,
    editFavoriteName,
    editSearch,
    getPagerLimit,
    getPagerValue,
    makeMockEnv,
    makeServerError,
    pagerNext,
    removeFacet,
    saveFavorite,
    serverState,
    toggleSaveFavorite,
    validateSearch,
} from "../../web_test_helpers";

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
        "form,false": `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>`,
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
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<list><field name="foo"/></list>`,
        "pivot,false": `<pivot/>`,
        "search,false": `<search><field name="foo" string="Foo"/></search>`,
        "search,4": `
            <search>
                <filter name="m2o" help="M2O" domain="[('m2o', '=', 1)]"/>
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
        "list,false": `<list><field name="name"/></list>`,
        "form,false": `<form><field name="name"/></form>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner, Pony, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
    {
        id: 2,
        xml_id: "action_2",
        name: "Partner",
        res_id: 2,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[74, "form"]],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        mobile_view_mode: "kanban",
        type: "ir.actions.act_window",
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
        type: "ir.actions.act_window",
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
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    },
    {
        id: 8,
        xml_id: "action_8",
        name: "Favorite Ponies",
        res_model: "pony",
        type: "ir.actions.act_window",
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
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    },
]);

test("can execute act_window actions from db ID", async () => {
    stepAllNetworkCalls();
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_control_panel").toHaveCount(1, { message: "should have rendered a control panel" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
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
    await mountWithCleanup(WebClient);
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    await contains(".o_data_row:eq(0) .o_data_cell").click();
    expect.verifySteps([]);
});

test("click on open form view button when there is no form in the action", async () => {
    Pony._views[
        "list,false"
    ] = `<list editable="top" open_form_view="1"><field name="name"/></list>`;
    stepAllNetworkCalls();
    await mountWithCleanup(WebClient);
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    await contains(".o_data_row:eq(0) .o_list_record_open_form_view").click();
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect.verifySteps(["get_views", "web_read"]);
});

test("click on new record button in list when there is no form in the action", async () => {
    stepAllNetworkCalls();
    await mountWithCleanup(WebClient);
    await getService("action").doAction(9);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
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

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_cp_action_menus .o_dropdown_title").toHaveCount(0); // no action menu

    await contains("input.form-check-input").click();
    expect('.o_cp_action_menus button.dropdown-toggle:contains("Print")').toBeVisible();
    expect('.o_cp_action_menus button.dropdown-toggle:contains("Action")').toBeVisible();
});

test.tags("desktop");
test("can switch between views", async () => {
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });

    // switch to kanban view
    await switchView("kanban");
    expect(".o_list_view").toHaveCount(0, { message: "should no longer display the list view" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should display the kanban view" });

    // switch back to list view
    await switchView("list");
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_kanban_view").toHaveCount(0, {
        message: "should no longer display the kanban view",
    });

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(0, { message: "should no longer display the list view" });
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "should have opened the correct record",
    });

    // go back to list view using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(".o_form_view").toHaveCount(0, { message: "should no longer display the form view" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
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
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1 patched",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
        },
    ]);
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1, { message: "should display the kanban view" });
    // quick create record and click Edit
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
        "web_search_read",
        "web_search_read",
        "onchange",
        "name_create",
        "web_read",
        "web_read",
    ]);
});

test.tags("desktop");
test("orderedBy in context is not propagated when executing another action", async () => {
    expect.assertions(6);

    Partner._views["form,false"] = `
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
        },
    ];

    let searchReadCount = 1;
    onRpc("web_search_read", ({ model, sort, kwargs }) => {
        if (searchReadCount === 1) {
            expect(model).toBe("partner");
            expect(sort).toBe(undefined);
        }
        if (searchReadCount === 2) {
            expect(model).toBe("partner");
            expect(kwargs.order).toBe("foo ASC");
        }
        if (searchReadCount === 3) {
            expect(model).toBe("pony");
            expect(sort).toBe(undefined);
        }
        searchReadCount += 1;
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    // Sort records
    await contains(".o_list_view th.o_column_sortable").click();
    // Get to the form view of the model, on the first record
    await contains(".o_data_cell").click();
    // Execute another action by clicking on the button within the form
    await contains('button[name="8"]').click();
});

test.tags("desktop");
test("breadcrumbs are updated when switching between views", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners");

    // switch to kanban view
    await switchView("kanban");
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners");

    // open a record in form view
    await contains(".o_kanban_view .o_kanban_record").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // go back to kanban view using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);

    // switch back to list view
    await switchView("list");
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // go back to list view using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_list_view").toHaveCount(1, { message: "should be back on list view" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
});

test.tags("desktop");
test("switch buttons are updated when switching between views", async () => {
    await mountWithCleanup(WebClient);
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

    // switch to kanban view
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

    // switch back to list view
    await switchView("list");
    expect(".o_control_panel .o_switch_view").toHaveCount(2, {
        message: "should still have two switch buttons (list and kanban)",
    });
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list should now be the active view",
    });

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_control_panel .o_switch_view").toHaveCount(0, {
        message: "should not have any switch buttons",
    });

    // go back to list view using the breadcrumbs
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
    Partner._views["list,false"] = `<list limit="3"><field name="foo"/></list>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(4);
    expect(".o_control_panel .o_pager_value").toHaveText("1-5", {
        message: "value should be correct for kanban",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for kanban",
    });

    // switch to list view
    await switchView("list");
    expect(".o_control_panel .o_pager_value").toHaveText("1-3", {
        message: "value should be correct for list",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for list",
    });

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_control_panel .o_pager_value").toHaveText("1", {
        message: "value should be correct for form",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("3", {
        message: "limit should be correct for form",
    });

    // go back to list view using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_control_panel .o_pager_value").toHaveText("1-3", {
        message: "value should be correct for list",
    });
    expect(".o_control_panel .o_pager_limit").toHaveText("5", {
        message: "limit should be correct for list",
    });

    // switch back to kanban view
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
    Partner._views["form,false"] = /* xml */ `
        <form>
            <group>
                <field name="display_name" />
                <field name="m2o" />
            </group>
        </form>`;

    onRpc("get_formview_action", ({ args, model }) => {
        return {
            res_id: args[0][0],
            res_model: model,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // 5 records initially
    expect(".o_data_row").toHaveCount(5);

    await contains(".o_data_row:first-of-type .o_data_cell").click();

    // Open 1 / 5
    expect(".o_field_char input").toHaveValue("First record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(5);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();

    // Click on M2O -> 1 / 1
    expect(".o_field_char input").toHaveValue("Third record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(1);

    await contains(".o_back_button").click();

    // Back to 1 / 5
    expect(".o_field_char input").toHaveValue("First record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(5);

    await pagerNext();

    // Next page -> 2 / 5
    expect(".o_field_char input").toHaveValue("Second record");
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(5);

    await contains(".o_field_many2one .o_external_button", { visible: false }).click();

    // Click on M2O -> still 1 / 1
    expect(".o_field_char input").toHaveValue("Third record");
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(1);

    await contains(".o_back_button").click();

    // Back to 2 / 5
    expect(".o_field_char input").toHaveValue("Second record");
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(5);
});

test.tags("desktop");
test("domain is kept when switching between views", async () => {
    defineActions([
        {
            id: 3,
            name: "Partners",
            res_model: "partner",
            search_view_id: [4, "a custom search view"],
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [1, "kanban"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_data_row").toHaveCount(5);

    // activate a domain
    await toggleSearchBarMenu();
    await toggleMenuItem("M2O");
    expect(".o_data_row").toHaveCount(3);

    // switch to kanban
    await switchView("kanban");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);

    // remove the domain
    await contains(".o_searchview .o_facet_remove").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);

    // switch back to list
    await switchView("list");
    expect(".o_data_row").toHaveCount(5);
});

test.tags("desktop");
test("A new form view can be reloaded after a failed one", async () => {
    expect.errors(1);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "The list view should be displayed" });
    await runAllTimers(); // wait for the update of the router
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

    // Click on the first record
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, { message: "The form view should be displayed" });
    expect(".o_last_breadcrumb_item").toHaveText("First record");
    await runAllTimers(); // wait for the update of the router
    expect(browser.location.pathname).toBe("/odoo/action-3/1");

    // Delete the current record
    await contains(".o_cp_action_menus .fa-cog").click();
    await contains(".o_menu_item:contains(Delete)").click();
    expect(".modal").toHaveCount(1, { message: "a confirm modal should be displayed" });
    await contains(".modal-footer button.btn-primary").click();
    // The form view is automatically switched to the next record
    expect(".o_last_breadcrumb_item").toHaveText("Second record");
    await runAllTimers(); // wait for the update of the router
    expect(browser.location.pathname).toBe("/odoo/action-3/2");

    // Go back to the previous (now deleted) record
    browser.history.back();
    await runAllTimers();
    expect(browser.location.pathname).toBe("/odoo/action-3/1");
    // As the previous one is deleted, we go back to the list
    await runAllTimers(); // wait for the update of the router
    expect(".o_list_view").toHaveCount(1, { message: "should still display the list view" });
    // Click on the first record
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, {
        message: "The form view should still load after a previous failed update | reload",
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

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // switch to kanban view
    def = new Deferred();
    await switchView("kanban");
    expect(".o_list_view").toHaveCount(1, { message: "should still display the list view" });
    expect(".o_kanban_view").toHaveCount(0, { message: "shouldn't display the kanban view yet" });

    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, { message: "shouldn't display the list view anymore" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should now display the kanban view" });

    // switch back to list view
    def = new Deferred();
    await switchView("list");
    expect(".o_kanban_view").toHaveCount(1, { message: "should still display the kanban view" });
    expect(".o_list_view").toHaveCount(0, { message: "shouldn't display the list view yet" });

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(0, {
        message: "shouldn't display the kanban view anymore",
    });
    expect(".o_list_view").toHaveCount(1, { message: "should now display the list view" });

    // open a record in form view
    def = new Deferred();
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(1, { message: "should still display the list view" });
    expect(".o_form_view").toHaveCount(0, { message: "shouldn't display the form view yet" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);

    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, { message: "should no longer display the list view" });
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // go back to list view using the breadcrumbs
    def = new Deferred();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view").toHaveCount(1, { message: "should still display the form view" });
    expect(".o_list_view").toHaveCount(0, { message: "shouldn't display the list view yet" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    def.resolve();
    await animationFrame();
    expect(".o_form_view").toHaveCount(0, { message: "should no longer display the form view" });
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
});

test.tags("desktop");
test("breadcrumbs are updated when display_name changes", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // change the display_name
    await contains(".o_field_widget[name=display_name] input").edit("New name");
    await clickSave();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "New name",
    ]);
});

test.tags("desktop");
test('reverse breadcrumb works on accesskey "b"', async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
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
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // create a new record
    await clickListNew();
    expect(".o_form_view .o_form_editable").toHaveCount(1, {
        message: "should have opened the form view in edit mode",
    });

    // discard
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
        "has_group",
        "onchange",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("execute_action of type object are handled", async () => {
    expect.assertions(4);
    serverState.userContext = { some_key: 2 };

    onRpc("partner", "object", async function ({ args, kwargs }) {
        expect(kwargs).toEqual(
            {
                context: {
                    lang: "en",
                    uid: 7,
                    tz: "taht",
                    allowed_company_ids: [1],
                    some_key: 2,
                },
            },
            { message: "should call route with correct arguments" }
        );
        return this.env["partner"].write(args[0], { foo: "value changed" });
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "check initial value of 'yop' field",
    });

    // click on 'Call method' button (should call an Object method)
    await contains(".o_form_view button:contains(Call method)").click();
    expect(".o_field_widget[name=foo] input").toHaveValue("value changed", {
        message: "'yop' has been changed by the server, and should be updated in the UI",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "web_read",
        "object",
        "web_read",
    ]);
});

test.tags("desktop");
test("execute_action of type object: disable buttons (2)", async () => {
    Pony._views["form,44"] = `
        <form>
            <field name="name"/>
            <button string="Cancel" class="cancel-btn" special="cancel"/>
        </form>`;
    defineActions([
        {
            id: 4,
            name: "Create a Partner",
            res_model: "pony",
            target: "new",
            type: "ir.actions.act_window",
            views: [[44, "form"]],
        },
    ]);

    const def = new Deferred();
    // delay the opening of the dialog
    onRpc("onchange", () => def);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    // open first record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    // click on 'Execute action', to execute action 4 in a dialog
    await contains('.o_form_view button[name="4"]').click();
    expect(".o_form_button_create").toHaveProperty("disabled", true, {
        message: "control panel buttons should be disabled",
    });

    def.resolve();
    await animationFrame();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".o_form_button_create").not.toHaveProperty("disabled", true, {
        message: "control panel buttons should have been re-enabled",
    });

    await contains(".modal .cancel-btn").click();
    expect(".o_form_button_create").not.toHaveProperty("disabled", true, {
        message: "control panel buttons should still be enabled",
    });
});

test.tags("desktop");
test("view button: block ui attribute", async () => {
    Partner._views["form,false"] = `
            <form>
                <header>
                    <button name="4" string="Execute action" type="action" block-ui="1"/>
                </header>
            </form>`;

    const def = new Deferred();
    // delay the action
    onRpc("onchange", () => def);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    // open first record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o-main-components-container .o_blockUI").toHaveCount(0);

    // click on 'Execute action', to execute action 4
    await contains('.o_form_view button[name="4"]').click();
    expect(".o-main-components-container .o_blockUI").toHaveCount(1, {
        message: "interface should be blocked during loading",
    });

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o-main-components-container .o_blockUI").toHaveCount(0);
});

test("execute_action of type object raises error: re-enables buttons", async () => {
    expect.errors(1);

    onRpc("/web/dataset/call_button/*", () => {
        throw makeServerError({ message: "This is a user error" });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3, { viewType: "form" });
    expect(".o_form_view").toHaveCount(1);

    // save to ensure the presence of the create button
    await contains(".o_form_button_save").click();

    // click on 'Execute action', to execute action 4 in a dialog
    await click('.o_form_view button[name="object"]');
    expect(".o_form_button_create").toHaveProperty("disabled", true);
    await animationFrame();
    expect(".o_form_button_create").toHaveProperty("disabled", false);
});

test("execute_action of type object raises error in modal: re-enables buttons", async () => {
    expect.errors(1);
    Partner._views["form,false"] = `
            <form>
                <field name="display_name"/>
                <footer>
                    <button name="object" string="Call method" type="object"/>
                </footer>
            </form>`;

    onRpc("/web/dataset/call_button/*", () => {
        throw makeServerError();
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(5);
    expect(".modal .o_form_view").toHaveCount(1);
    await click('.modal footer button[name="object"]');
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal footer button").toHaveProperty("disabled", true);
    await animationFrame();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal footer button").not.toHaveProperty("disabled", true);
});

test.tags("desktop");
test("execute_action of type action are handled", async () => {
    stepAllNetworkCalls();
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    // click on 'Execute action' button (should execute an action)
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
        "has_group",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
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

    await mountWithCleanup(WebClient);
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
    onRpc("web_search_read", () => {
        throw makeServerError({ message: "Oups" });
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);

    await contains("button.oe_stat_button").click();
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
    expect.verifyErrors(["Oups"]);
});

test.tags("mobile");
test("execute smart button and fails on mobile", async () => {
    expect.errors(1);
    onRpc("web_search_read", () => {
        throw makeServerError({ message: "Oups" });
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_button_create:not([disabled]):visible").toHaveCount(1);

    await contains(".o-form-buttonbox .o_button_more").click();
    await contains("button.oe_stat_button").click();
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
    expect.verifyErrors(["Oups"]);
});

test.tags("desktop");
test("requests for execute_action of type object: disable buttons", async () => {
    let def = undefined;
    onRpc("web_read", () => def); // block the 'read' call
    onRpc("/web/dataset/call_button/*", () => false);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();

    // click on 'Call method' button (should call an Object method)
    def = new Deferred();
    await contains(".o_form_view button:contains(Call method)").click();

    // Buttons should be disabled
    expect(".o_form_view button:contains(Call method)").toHaveProperty("disabled", true, {
        message: "buttons should be disabled",
    });

    // Release the 'read' call
    def.resolve();
    await animationFrame();

    // Buttons should be enabled after the reload
    expect(".o_form_view button:contains(Call method)").not.toHaveProperty("disabled", true, {
        message: "buttons should not be disabled anymore",
    });
});

test.tags("desktop");
test("action with html help returned by a call_button", async () => {
    onRpc("/web/dataset/call_button/*", () => {
        return {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            help: "<p>I am not a helper</p>",
            domain: [[0, "=", 1]],
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await contains(".o_statusbar_buttons button").click();
    expect(".o_list_view .o_nocontent_help p").toHaveText("I am not a helper");
});

test.tags("desktop");
test("can open different records from a multi record view", async () => {
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open the first record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_breadcrumb .active").toHaveText("First record", {
        message: "breadcrumbs should contain the display_name of the opened record",
    });
    expect(".o_field_widget[name=foo] input").toHaveValue("yop", {
        message: "should have opened the correct record",
    });

    // go back to list view using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();

    // open the second record in form view
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
        "has_group",
        "web_read",
        "web_search_read",
        "web_read",
    ]);
});

test.tags("desktop");
test("restore previous view state when switching back", async () => {
    defineActions([
        {
            id: 3,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "graph"],
                [1, "kanban"],
                [false, "form"],
            ],
        },
    ]);
    Partner._views["graph,false"] = "<graph/>";

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_graph_renderer [data-mode='bar']").toHaveClass("active");
    expect(".o_graph_renderer [data-mode='line']").not.toHaveClass("active");

    // display line chart
    await contains(".o_graph_renderer [data-mode='line']").click();
    expect(".o_graph_renderer [data-mode='line']").toHaveClass("active");

    // switch to kanban and back to graph view
    await switchView("kanban");
    expect(".o_graph_renderer [data-mode='line']").toHaveCount(0);

    await switchView("graph");
    expect(".o_graph_renderer [data-mode='line']").toHaveClass("active");
});

test.tags("desktop");
test("can't restore previous action if form is invalid", async () => {
    Partner._fields.foo = fields.Char({ required: true });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=foo]").toHaveClass("o_required_modifier");

    await contains(".o_field_widget[name=display_name] input").edit("make record dirty");
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
            id: 3,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "pivot"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_control_panel .o_switch_view.o_list").toHaveClass("active", {
        message: "list button in control panel is active",
    });
    expect(".o_control_panel .o_switch_view.o_pivot").not.toHaveClass("active", {
        message: "pivot button in control panel is not active",
    });

    // switch to pivot view
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
    Partner._views["search,false"] = `
        <search>
            <group>
            <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_table").not.toHaveClass("o_list_table_grouped", {
        message: "list view is not grouped",
    });

    // open group by dropdown
    await toggleSearchBarMenu();
    // click on foo link
    await toggleMenuItem("foo");
    expect(".o_list_table").toHaveClass("o_list_table_grouped", {
        message: "list view is now grouped",
    });
});

test.tags("desktop");
test("can open a many2one external window", async () => {
    Partner._views["search,false"] = `
        <search>
            <group>
                <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;
    Partner._views["form,false"] = `
        <form>
            <field name="foo"/>
            <field name="m2o"/>
        </form>`;

    stepAllNetworkCalls();
    onRpc("get_formview_action", () => {
        return {
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            res_id: 3,
            views: [[false, "form"]],
        };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    // open first record in form view
    await contains(".o_data_row .o_data_cell").click();
    // click on external button for m2o
    await contains(".o_external_button", { visible: false }).click();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
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

    await mountWithCleanup(WebClient);
    await getService("action").doAction(4);
    // open record in form view
    await contains(".o_kanban_record").click();
    await contains('.o_field_widget[name="foo"] input').edit("pinkypie");
    // go back to kanban view
    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(".modal").toHaveCount(0, { message: "should not display a modal dialog" });
    expect(".o_form_view").toHaveCount(0, { message: "should no longer be in form view" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should be in kanban view" });
});

test.tags("desktop");
test("limit set in action is passed to each created controller", async () => {
    await mountWithCleanup(WebClient);
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

    // switch to kanban view
    await switchView("kanban");
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
});

test.tags("desktop");
test("go back to a previous action using the breadcrumbs", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // push another action on top of the first one, and come back to the form view
    await getService("action").doAction(4);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
    ]);

    // push again the other action on top of the first one, and come back to the list view
    await getService("action").doAction(4);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "First record",
        "Partners Action 4",
    ]);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a:first").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
});

test.tags("desktop");
test("form views are restored in edit when coming back in breadcrumbs", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    // do some other action
    await getService("action").doAction(4);

    // go back to form view
    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
});

test.tags("desktop");
test("form views restore the correct id in url when coming back in breadcrumbs", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    // open a record in form view
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await runAllTimers(); // wait for the router to update its state
    expect(router.current.resId).toBe(1);

    // do some other action
    await getService("action").doAction(4);
    await runAllTimers(); // wait for the router to update its state
    expect(router.current).not.toInclude("resId");

    // go back to form view
    await contains(".o_control_panel .breadcrumb a:eq(1)").click();
    await runAllTimers(); // wait for the router to update its state
    expect(router.current.resId).toBe(1);
});

test.tags("desktop");
test("honor group_by specified in actions context", async () => {
    defineActions([
        {
            id: 3,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            context: "{'group_by': 'm2o'}",
            views: [[false, "list"]],
        },
    ]);
    Partner._views["search,false"] = `
        <search>
            <group>
            <filter name="foo" string="Foo" context="{'group_by': 'foo'}"/>
            </group>
        </search>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_table_grouped").toHaveCount(1, { message: "should be grouped" });
    expect(".o_group_header").toHaveCount(2, {
        message: "should be grouped by 'bar' (two groups) at first load",
    });

    // groupby 'foo' using the searchview
    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(".o_group_header").toHaveCount(5, {
        message: "should be grouped by 'foo' (five groups)",
    });

    // remove the groupby in the searchview
    await contains(".o_control_panel .o_searchview .o_facet_remove").click();
    expect(".o_list_table_grouped").toHaveCount(1, { message: "should still be grouped" });
    expect(".o_group_header").toHaveCount(2, {
        message: "should be grouped by 'bar' (two groups) at reload",
    });
});

test("switch request to unknown view type", async () => {
    defineActions([
        {
            id: 33,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [1, "kanban"],
            ],
        },
    ]);

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(33);
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });
    // try to open a record in a form view
    contains(".o_list_view .o_data_row:first").click();
    expect(".o_list_view").toHaveCount(1, { message: "should still display the list view" });
    expect(".o_form_view").toHaveCount(0, { message: "should not display the form view" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test.tags("desktop");
test("execute action with unknown view type", async () => {
    defineActions([
        {
            id: 33,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "unknown"], // typically, an enterprise-only view on a community db
                [false, "kanban"],
                [false, "form"],
            ],
        },
    ]);
    await mountWithCleanup(WebClient);
    await expect(getService("action").doAction(33)).rejects.toThrow(
        /View types not defined unknown found in act_window action 33/
    );
});

test("flags field of ir.actions.act_window is used", async () => {
    // more info about flags field : https://github.com/odoo/odoo/commit/c9b133813b250e89f1f61816b0eabfb9bee2009d
    defineActions([
        {
            id: 43,
            name: "Partners",
            res_id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            flags: {
                mode: "edit",
            },
            views: [[false, "form"]],
        },
        {
            id: 44,
            name: "Partners",
            res_id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            flags: {
                mode: "readonly",
            },
            views: [[false, "form"]],
        },
    ]);

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);

    // action 43 -> form in edit mode
    await getService("action").doAction(43);
    expect(".o_form_view .o_form_editable").toHaveCount(1, {
        message: "should display the form view in edit mode",
    });

    // action 44 -> form in readonly mode
    await getService("action").doAction(44);
    expect(".o_form_view .o_form_readonly").toHaveCount(1, {
        message: "should display the form view in readonly mode",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_read",
    ]);
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
            type: "ir.actions.act_window",
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

    onRpc("create_or_replace", ({ args }) => {
        expect(args[0].domain).toBe(`[("m2o", "=", 1)]`);
        expect(args[0].context).toEqual({
            group_by: [],
            shouldBeInFilterContext: true,
        });
        return 3; // fake filter id
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(33);
    expect(".o_data_row").toHaveCount(5, { message: "should contain 5 records" });

    // filter on bar
    await toggleSearchBarMenu();
    await toggleMenuItem("M2O");
    expect(".o_data_row").toHaveCount(3);

    // save filter
    await toggleSaveFavorite();
    await editFavoriteName("some name");
    await saveFavorite();
});

test.tags("desktop");
test("list with default_order and favorite filter with no orderedBy", async () => {
    Partner._views["list,1"] = '<list default_order="foo desc"><field name="foo"/></list>';
    defineActions([
        {
            id: 100,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
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
        },
    ];
    await mountWithCleanup(WebClient);
    await getService("action").doAction(100);
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "yop", "plop", "gnap", "blip"],
        { message: "record should be in descending order as default_order applies" }
    );

    await toggleSearchBarMenu();
    await toggleMenuItem("favorite filter");
    expect(".o_control_panel .o_facet_values").toHaveText("favorite filter", {
        message: "favorite filter should be applied",
    });
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(["zoup", "plop", "gnap"], {
        message: "record should still be in descending order after default_order applied",
    });

    // go to formview and come back to listview
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(["zoup", "plop", "gnap"], {
        message: "order of records should not be changed, while coming back through breadcrumb",
    });

    // remove filter
    await removeFacet("favorite filter");
    expect(queryAllTexts(".o_data_row .o_data_cell")).toEqual(
        ["zoup", "yop", "plop", "gnap", "blip"],
        { message: "order of records should not be changed, after removing current filter" }
    );
});

test.tags("desktop");
test("action with default favorite and context.active_id", async () => {
    expect.assertions(4);

    defineActions([
        {
            id: 3,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            context: "{ 'active_id': 4, 'active_ids': [4], 'active_model': 'whatever' }",
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
        },
    ];
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([["bar", "=", 1]]);
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);

    expect(".o_list_view").toHaveCount(1);
    expect(".o_searchview .o_searchview_facet").toHaveCount(1);
    expect(".o_facet_value").toHaveText("favorite filter");
});

test.tags("desktop");
test("search menus are still available when switching between actions", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners Action 1"]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);

    await getService("action").doAction(3);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
        "Partners",
    ]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners Action 1"]);
    expect(".o_searchview_dropdown_toggler").toHaveCount(1);
});

test.tags("desktop");
test("current act_window action is stored in session_storage if possible", async () => {
    let expectedAction;
    patchWithCleanup(browser, {
        sessionStorage: Object.assign(Object.create(sessionStorage), {
            setItem(k, value) {
                expect(JSON.parse(value)).toEqual(expectedAction);
            },
        }),
    });
    await mountWithCleanup(WebClient);

    // execute an action that can be stringified -> should be stored
    expectedAction = MockServer.current.actions[3];
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    // execute an action that can't be stringified -> should not crash
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

test.tags("desktop");
test("destroy action with lazy loaded controller", async () => {
    redirect("/odoo/action-3/2");

    await mountWithCleanup(WebClient);
    await animationFrame(); // blank component
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
    Partner._views["form,false"] = `
        <form>
            <field name="display_name"/>
            <field name="foo"/>
            <field name="bar" readonly="1"/>
        </form>`;

    onRpc("get_formview_action", () => {
        return {
            res_id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);

    // execute an action and create a new record
    await getService("action").doAction(3);
    await clickListNew();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_form_uri:contains(First record)").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners", "New"]);

    // set form view dirty and open m2o record
    await contains('.o_field_widget[name="display_name"] input').edit("test");
    await contains(".o_field_widget[name=foo] input").edit("val");
    await contains(".o_form_uri").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "test",
        "First record",
    ]);
    // go back to test using the breadcrumbs
    await contains(".o_control_panel .breadcrumb-item a:eq(1)").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners", "test"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
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
        id: 8,
        name: "Favorite Ponies",
        res_model: "pony",
        type: "ir.actions.act_window",
        context: "{}", // need a context to evaluate
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

    await mountWithCleanup(WebClient);

    // execute an action and open a record
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    // execute the custom action from the action menu
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
            type: "ir.actions.act_window",
            res_id: 2,
            views: [[44, "form"]],
        },
    ]);
    Partner._views["form,44"] = '<form><field name="m2o"/></form>';

    onRpc("get_formview_action", () => {
        return {
            res_id: 3,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(999);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Second record"]);

    // push another action in the breadcrumb
    await contains(".o_field_many2one .o_external_button", { visible: false }).click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
        "Third record",
    ]);

    // go back to the form view
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Second record"]);
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
    onRpc("get_formview_action", () => {
        return { ...action, res_id: 3 };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(999, { props: { resIds: [1, 2] } });
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["First record"]);
    expect(".o_control_panel .o_pager_counter").toHaveText("1 / 2");

    // load another id on current action (through pager)
    await contains(".o_pager_next").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Second record"]);
    expect(".o_control_panel .o_pager_counter").toHaveText("2 / 2");

    // push another action in the breadcrumb
    await contains(".o_field_many2one .o_external_button", { visible: false }).click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Second record",
        "Third record",
    ]);

    // restore previous action through breadcrumb
    await contains(".o_control_panel .breadcrumb a").click();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Second record"]);
    expect(".o_control_panel .o_pager_counter").toHaveText("2 / 2");
});

test.tags("desktop");
test("open a record, come back, and create a new record", async () => {
    await mountWithCleanup(WebClient);

    // execute an action and open a record
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(5);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb-item a").click();
    expect(".o_list_view").toHaveCount(1);

    // create a new record
    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
});

test.tags("desktop");
test("open form view, use the pager, execute action, and come back", async () => {
    await mountWithCleanup(WebClient);

    // execute an action and open a record
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(5);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("First record");

    // switch to second record
    await contains(".o_pager_next").click();
    expect(".o_field_widget[name=display_name] input").toHaveValue("Second record");

    // execute an action from the second record
    await contains(".o_statusbar_buttons button[name='4']").click();
    expect(".o_kanban_view").toHaveCount(1);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb-item:eq(1) a").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("Second record");
});

test.tags("desktop");
test("create a new record in a form view, execute action, and come back", async () => {
    await mountWithCleanup(WebClient);

    // execute an action and create a new record
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await clickListNew();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_field_widget[name=display_name] input").edit("another record");
    await contains(".o_form_button_save").click();
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    // execute an action from the second record
    await contains(".o_statusbar_buttons button[name='4']").click();
    expect(".o_kanban_view").toHaveCount(1);

    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb-item:eq(1) a").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_field_widget[name=display_name] input").toHaveValue("another record");
});

test("onClose should be called only once with right parameters", async () => {
    expect.assertions(4);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2); // main form view
    await getService("action").doAction(5, {
        // form view in target new
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
    expect(".modal").toHaveCount(0);
});

test.tags("desktop");
test("search view should keep focus during do_search", async () => {
    // One should be able to type something in the search view, press on enter to
    // make the facet and trigger the search, then do this process
    // over and over again seamlessly.
    // Verifying the input's value is a lot trickier than verifying the search_read
    // because of how native events are handled in tests
    const searchPromise = new Deferred();
    onRpc("web_search_read", async ({ kwargs }) => {
        expect.step("search_read " + kwargs.domain);
        if (JSON.stringify(kwargs.domain) === JSON.stringify([["foo", "ilike", "m"]])) {
            await searchPromise;
        }
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    await editSearch("m");
    await validateSearch();
    expect.verifySteps(["search_read ", "search_read foo,ilike,m"]);

    // Triggering the do_search above will kill the current searchview Input
    await editSearch("o");
    // We have something in the input of the search view. Making the search_read
    // return at this point will trigger the redraw of the view.
    // However we want to hold on to what we just typed
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
    await mountWithCleanup(WebClient, { env });

    // execute an action and edit existing record
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
    Partner._views["form,false"] = `<form><field name="foo"/></form>`;

    onRpc("onchange", () => {
        return {
            value: {},
            warning: {
                title: "Warning",
                message: "Everything is alright",
                type: "dialog",
            },
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    await clickListNew();
    expect(".modal.o_technical_modal").toHaveCount(1, {
        message: "Warning modal should be opened",
    });

    await contains(".modal.o_technical_modal button.btn-primary").click();
    expect(".modal.o_technical_modal").toHaveCount(0, {
        message: "Warning modal should be closed",
    });
});

test("do not call clearUncommittedChanges() when target=new and dialog is opened", async () => {
    await mountWithCleanup(WebClient);

    // Open Partner form view and enter some text
    await getService("action").doAction(3, { viewType: "form" });
    expect(".o_action_manager .o_form_view .o_form_editable").toHaveCount(1);

    await contains(".o_field_widget[name=display_name] input").edit("TEST");
    // Open dialog without saving should not ask to discard
    await getService("action").doAction(5);
    expect(".o_action_manager .o_form_view .o_form_editable").toHaveCount(1);
    expect(".o_dialog .o_view_controller").toHaveCount(1);
});

test("do not pushState when target=new and dialog is opened", async () => {
    await mountWithCleanup(WebClient);

    // Open Partner form in create mode
    await getService("action").doAction(3, { viewType: "form" });
    await runAllTimers();
    const prevUrlState = Object.assign({}, router.current);
    // Edit another partner in a dialog
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

test.tags("desktop");
test("do not restore after action button clicked on desktop", async () => {
    Partner._views["form,false"] = `
        <form>
            <header>
                <button name="do_something" string="Call button" type="object"/>
            </header>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>`;

    onRpc("/web/dataset/call_button/*", () => true);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3, { viewType: "form", props: { resId: 1 } });
    await contains("div[name='display_name'] input").edit("Edited value");
    expect(".o_form_button_save").toBeVisible();
    expect(".o_statusbar_buttons button[name=do_something]").toBeVisible();

    await contains(".o_statusbar_buttons button[name=do_something]").click();
    expect(".o_form_buttons_view .o_form_button_save").not.toBeVisible();
});

test.tags("mobile");
test("do not restore after action button clicked on mobile", async () => {
    Partner._views["form,false"] = `
        <form>
            <header>
                <button name="do_something" string="Call button" type="object"/>
            </header>
            <sheet>
                <field name="display_name"/>
            </sheet>
        </form>`;

    onRpc("/web/dataset/call_button/*", () => true);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3, { viewType: "form", props: { resId: 1 } });
    await contains("div[name='display_name'] input").edit("Edited value");
    expect(".o_form_button_save").toBeVisible();
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    expect(".o-dropdown-item-unstyled-button button[name=do_something]").toBeVisible();

    await contains(".o-dropdown-item-unstyled-button button[name=do_something]").click();
    expect(".o_form_buttons_view .o_form_button_save").not.toBeVisible();
});

test("debugManager is active for views", async () => {
    serverState.debug = "1";
    onRpc("has_access", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o-dropdown--menu .o-dropdown-item:contains('View: Kanban')").toHaveCount(0);
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".o-dropdown--menu .o-dropdown-item:contains('View: Kanban')").toHaveCount(1);
});

test.tags("desktop");
test("reload a view via the view switcher keep state", async () => {
    onRpc("read_group", () => {
        expect.step("read_group");
    });

    await mountWithCleanup(WebClient);
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
        "read_group", // initial read_group
        "read_group", // read_group at reload after switch view
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

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1, {
        props: {
            globalState: { searchModel },
        },
    });
});

test.tags("desktop");
test("window action in target new fails (onchange) on desktop", async () => {
    expect.errors(1);

    onRpc("partner", "onchange", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = /*xml*/ `
        <form>
            <header>
                <button name="5" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    await contains(".o_form_view button[name='5']").click();
    await waitFor(".modal"); // errors are async
    expect(".modal").toHaveCount(1);
    expect(".modal .o_error_dialog").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Validation Error");
});

test.tags("mobile");
test("window action in target new fails (onchange) on mobile", async () => {
    expect.errors(1);

    onRpc("partner", "onchange", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = /*xml*/ `
        <form>
            <header>
                <button name="5" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(".o-dropdown-item-unstyled-button button[name='5']").click();
    await waitFor(".modal"); // errors are async
    expect(".modal").toHaveCount(1);
    expect(".modal .o_error_dialog").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Validation Error");
});

test.tags("desktop");
test("Uncaught error in target new is catch only once on desktop", async () => {
    expect.errors(1);

    defineActions([
        {
            id: 26,
            name: "Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    ]);

    onRpc("partner", "web_search_read", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = /*xml*/ `
        <form>
            <header>
                <button name="26" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    await contains(".o_form_view button[name='26']").click();
    await waitFor(".modal"); // errors are async
    expect(".modal").toHaveCount(1);
    expect(".modal .o_error_dialog").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Validation Error");
});

test.tags("mobile");
test("Uncaught error in target new is catch only once on mobile", async () => {
    expect.errors(1);

    defineActions([
        {
            id: 26,
            name: "Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    ]);

    onRpc("partner", "web_search_read", () => {
        throw makeServerError({ type: "ValidationError" });
    });

    Partner._views["form,74"] = /*xml*/ `
        <form>
            <header>
                <button name="26" string="Test" type="action"/>
            </header>
            <field name="display_name"/>
        </form>`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(".o-dropdown-item-unstyled-button button[name='26']").click();
    await waitFor(".modal"); // errors are async
    expect(".modal").toHaveCount(1);
    expect(".modal .o_error_dialog").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Validation Error");
});

test("action and get_views rpcs are cached", async () => {
    class IrActionsAct_Window extends models.Model {
        _name = "ir.actions.act_window";
    }
    defineModels([IrActionsAct_Window]);

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);

    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    expect.verifySteps(["web_search_read"]);

    await getService("orm").unlink("ir.actions.act_window", [333]);
    expect.verifySteps(["unlink"]);
    await getService("action").doAction(1);
    // cache was cleared => reload the action
    expect.verifySteps(["/web/action/load", "web_search_read"]);
});

test.tags("desktop");
test("pushState also changes the title of the tab", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3); // list view

    const titleService = getService("title");
    expect(titleService.current).toBe("Partners");

    await contains(".o_data_row .o_data_cell").click();
    expect(titleService.current).toBe("First record");

    await contains(".o_pager_next").click();
    expect(titleService.current).toBe("Second record");
});

test("action group_by of type string", async () => {
    Partner._views["pivot,false"] = `<pivot/>`;
    await mountWithCleanup(WebClient);
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
        type: "ir.actions.act_window",
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

    await mountWithCleanup(WebClient);
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
        "list,false": `<list><field name="foo"/></list>`,
        "search,false": `<search/>`,
    };

    await mountWithCleanup(WebClient);
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
        "kanban,false": `
            <kanban sample="1" default_group_by="write_date:month">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        "pivot,false": `
            <pivot sample="1">
                <field name="write_date" type="row"/>
            </pivot>`,
        "search,false": `<search/>`,
    };
    onRpc("web_read_group", () => {
        return {
            groups: [
                {
                    date_count: 0,
                    "write_date:month": "December 2022",
                    __range: {
                        "write_date:month": {
                            from: "2022-12-01",
                            to: "2023-01-01",
                        },
                    },
                    __domain: [
                        ["write_date", ">=", "2022-12-01"],
                        ["write_date", "<", "2023-01-01"],
                    ],
                },
            ],
            length: 1,
        };
    });

    await mountWithCleanup(WebClient);
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
    Partner._views["form,false"] = `
        <form>
            <button type="action" name="3" string="Open Action 3" class="my_btn"/>
        </form>`;

    await mountWithCleanup(WebClient);
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
    // open action menu and delete
    await contains(".o_cp_action_menus .fa-cog").click();
    await toggleMenuItem("Delete");
    expect(".o_dialog").toHaveCount(1);

    // confirm
    await contains(".o_dialog .modal-footer .btn-primary").click();

    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item")).toEqual(["", "First record", "Partners"]);
    expect(".o_breadcrumb .active").toHaveText("Second record");

    // click on "First record" in breadcrumbs, which doesn't exist anymore
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
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    getService("dialog").add(FormViewDialog, { resModel: "partner", resId: 1 });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);

    await contains(".o_dialog .o_form_view .o_statusbar_buttons button[name='4']").click();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_dialog").toHaveCount(0);
});
