import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne, scroll, waitFor } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, onWillStart, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    getDropdownMenu,
    getService,
    makeMockEnv,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
    switchView,
    webModels,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import { listView } from "@web/views/list/list_view";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { WebClient } from "@web/webclient/webclient";
import { redirect } from "@web/core/utils/urls";

const { ResCompany, ResPartner, ResUsers } = webModels;

class Partner extends models.Model {
    _rec_name = "display_name";

    o2m = fields.One2many({ relation: "partner", relation_field: "bar" });

    _records = [
        { id: 1, display_name: "First record", o2m: [2, 3] },
        {
            id: 2,
            display_name: "Second record",
            o2m: [1, 4, 5],
        },
        { id: 3, display_name: "Third record", o2m: [] },
        { id: 4, display_name: "Fourth record", o2m: [] },
        { id: 5, display_name: "Fifth record", o2m: [] },
    ];
    _views = {
        form: `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        list: `<list><field name="display_name"/></list>`,
        "list,2": `<list limit="3"><field name="display_name"/></list>`,
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
        list: '<list><field name="name"/></list>',
        form: `<form><field name="name"/></form>`,
    };
}

defineModels([Partner, Pony, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[1, "kanban"]],
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
        id: 5,
        xml_id: "action_5",
        name: "Create a Partner",
        res_model: "partner",
        target: "new",
        views: [[false, "form"]],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        views: [
            [1, "kanban"],
            [2, "list"],
            [false, "form"],
        ],
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
]);

const actionRegistry = registry.category("actions");
const actionHandlersRegistry = registry.category("action_handlers");

test("can execute actions from id, xmlid and tag", async () => {
    defineActions([
        {
            id: 10,
            tag: "client_action_by_db_id",
            target: "main",
            type: "ir.actions.client",
        },
        {
            id: 20,
            xml_id: "some_action",
            tag: "client_action_by_xml_id",
            target: "main",
            type: "ir.actions.client",
        },
        {
            id: 30,
            path: "my_action",
            tag: "client_action_by_path",
            target: "main",
            type: "ir.actions.client",
        },
    ]);
    actionRegistry
        .add("client_action_by_db_id", () => expect.step("client_action_db_id"))
        .add("client_action_by_xml_id", () => expect.step("client_action_xml_id"))
        .add("client_action_by_path", () => expect.step("client_action_path"))
        .add("client_action_by_tag", () => expect.step("client_action_tag"))
        .add("client_action_by_object", () => expect.step("client_action_object"));

    await makeMockEnv();
    await getService("action").doAction(10);
    expect.verifySteps(["client_action_db_id"]);
    await getService("action").doAction("some_action");
    expect.verifySteps(["client_action_xml_id"]);
    await getService("action").doAction("my_action");
    expect.verifySteps(["client_action_path"]);
    await getService("action").doAction("client_action_by_tag");
    expect.verifySteps(["client_action_tag"]);
    await getService("action").doAction({
        tag: "client_action_by_object",
        target: "current",
        type: "ir.actions.client",
    });
    expect.verifySteps(["client_action_object"]);
});

test("action doesn't exists", async () => {
    expect.assertions(1);
    await makeMockEnv();
    try {
        await getService("action").doAction({
            tag: "this_is_a_tag",
            target: "current",
            type: "ir.not_action.error",
        });
    } catch (e) {
        expect(e.message).toBe(
            "The ActionManager service can't handle actions of type ir.not_action.error"
        );
    }
});

test("getCurrentAction", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    const currentAction = await getService("action").currentAction;
    expect(currentAction).toEqual({
        binding_type: "action",
        binding_view_types: "list,form",
        id: 1,
        type: "ir.actions.act_window",
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[1, "kanban"]],
        context: {},
        embedded_action_ids: [],
        group_ids: [],
        limit: 80,
        mobile_view_mode: "kanban",
        target: "current",
        view_ids: [],
        view_mode: "list,form",
        cache: true,
    });
});

test("getCurrentAction (virtual controller)", async () => {
    stepAllNetworkCalls();
    class ClientAction extends Component {
        static template = xml`<div class="o_client_action_test">Hello World</div>`;
        static props = ["*"];
        static path = "plop";
        setup() {
            onWillStart(async () => {
                const currentAction = await getService("action").currentAction;
                expect.step(currentAction);
            });
        }
    }
    actionRegistry.add("HelloWorldTest", ClientAction);

    redirect("/odoo/action-1/plop");
    await mountWithCleanup(WebClient);

    await animationFrame();

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load_breadcrumbs",
        "/web/action/load",
        {
            binding_type: "action",
            binding_view_types: "list,form",
            id: 1,
            type: "ir.actions.act_window",
            xml_id: "action_1",
            name: "Partners Action 1",
            res_model: "partner",
            views: [[1, "kanban"]],
            context: {},
            embedded_action_ids: [],
            group_ids: [],
            limit: 80,
            mobile_view_mode: "kanban",
            target: "current",
            view_ids: [],
            view_mode: "list,form",
            cache: true,
        },
    ]);
});

test("action in handler registry", async () => {
    await makeMockEnv();
    actionHandlersRegistry.add("ir.action_in_handler_registry", ({ action }) =>
        expect.step(action.type)
    );
    await getService("action").doAction({
        tag: "this_is_a_tag",
        target: "current",
        type: "ir.action_in_handler_registry",
    });
    expect.verifySteps(["ir.action_in_handler_registry"]);
});

test("properly handle case when action id does not exist", async () => {
    expect.errors(1);
    await mountWithCleanup(WebClient);
    getService("action").doAction(4448);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(`.modal .o_error_dialog`).toHaveCount(1);
    expect(".o_error_dialog .modal-body").toHaveText("The action 4448 does not exist");
});

test("properly handle case when action path does not exist", async () => {
    expect.errors(1);
    await mountWithCleanup(WebClient);
    getService("action").doAction("plop");
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(`.modal .o_error_dialog`).toHaveCount(1);
    expect(".o_error_dialog .modal-body").toHaveText('The action "plop" does not exist');
});

test("properly handle case when action xmlId does not exist", async () => {
    expect.errors(1);
    await mountWithCleanup(WebClient);
    getService("action").doAction("not.found.action");
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(`.modal .o_error_dialog`).toHaveCount(1);
    expect(".o_error_dialog .modal-body").toHaveText(
        'The action "not.found.action" does not exist'
    );
});

test("actions can be cached", async () => {
    onRpc("/web/action/load", async (request) => {
        const { params } = await request.json();
        expect.step(params.context);
    });

    await makeMockEnv();

    // With no additional params
    await getService("action").loadAction(3);
    await getService("action").loadAction(3);

    // With specific context
    await getService("action").loadAction(3, { configuratorMode: "add" });
    await getService("action").loadAction(3, { configuratorMode: "edit" });

    // With same active_id
    await getService("action").loadAction(3, { active_id: 1 });
    await getService("action").loadAction(3, { active_id: 1 });

    // With active_id change
    await getService("action").loadAction(3, { active_id: 2 });

    // With same active_ids
    await getService("action").loadAction(3, { active_ids: [1, 2] });
    await getService("action").loadAction(3, { active_ids: [1, 2] });

    // With active_ids change
    await getService("action").loadAction(3, { active_ids: [1, 2, 3] });

    // With same active_model
    await getService("action").loadAction(3, { active_model: "a" });
    await getService("action").loadAction(3, { active_model: "a" });

    // With active_model change
    await getService("action").loadAction(3, { active_model: "b" });

    // should load from server once per active_id/active_ids/active_model change, nothing else
    const baseCtx = {
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    };
    expect.verifySteps([
        { ...baseCtx },
        { ...baseCtx, configuratorMode: "add" },
        { ...baseCtx, configuratorMode: "edit" },
        { ...baseCtx, active_id: 1 },
        { ...baseCtx, active_id: 2 },
        { ...baseCtx, active_ids: [1, 2] },
        { ...baseCtx, active_ids: [1, 2, 3] },
        { ...baseCtx, active_model: "a" },
        { ...baseCtx, active_model: "b" },
    ]);
});

test("action cache: additionalContext is used on the key", async () => {
    onRpc("/web/action/load", () => {
        expect.step("server loaded");
    });

    await makeMockEnv();
    const actionParams = {
        additionalContext: {
            some: { deep: { nested: "Robert" } },
        },
    };

    let action = await getService("action").loadAction(3, actionParams);
    expect.verifySteps(["server loaded"]);
    expect(action.context).toEqual(actionParams);

    // Modify the action in place
    action.context.additionalContext.some.deep.nested = "Nesta";

    // Change additionalContext and reload
    actionParams.additionalContext.some.deep.nested = "Marley";
    action = await getService("action").loadAction(3, actionParams);
    expect.verifySteps(["server loaded"]);
    expect(action.context).toEqual(actionParams);
});

test.tags("desktop");
test('action with "no_breadcrumbs" set to true', async () => {
    defineActions([
        {
            id: 42,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [1, "kanban"],
                [false, "list"],
            ],
            context: { no_breadcrumbs: true },
        },
    ]);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_breadcrumb").toHaveCount(1);
    // push another action flagged with 'no_breadcrumbs=true'
    await getService("action").doAction(42);
    await waitFor(".o_kanban_view");
    expect(".o_breadcrumb").toHaveCount(0);
    await contains(".o_switch_view.o_list").click();
    await waitFor(".o_list_view");
    expect(".o_breadcrumb").toHaveCount(0);
});

test("document's title is updated when an action is executed", async () => {
    await mountWithCleanup(WebClient);
    await animationFrame();
    let currentTitle = getService("title").getParts();
    expect(currentTitle).toEqual({});
    let currentState = router.current;
    await getService("action").doAction(4);
    await animationFrame();
    currentTitle = getService("title").getParts();
    expect(currentTitle).toEqual({ action: "Partners Action 4" });
    currentState = router.current;
    expect(currentState).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
    });

    await getService("action").doAction(8);
    await animationFrame();
    currentTitle = getService("title").getParts();
    expect(currentTitle).toEqual({ action: "Favorite Ponies" });
    currentState = router.current;
    expect(currentState).toEqual({
        action: 8,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
        ],
    });

    await contains(".o_data_row .o_data_cell").click();
    await animationFrame();
    currentTitle = getService("title").getParts();
    expect(currentTitle).toEqual({ action: "Twilight Sparkle" });
    currentState = router.current;
    expect(currentState).toEqual({
        action: 8,
        resId: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
            {
                action: 8,
                resId: 4,
                displayName: "Twilight Sparkle",
                view_type: "form",
            },
        ],
    });
});

test.tags("desktop");
test('handles "history_back" event', async () => {
    let list;
    patchWithCleanup(listView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            list = this;
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(4);
    await getService("action").doAction(3);
    expect("ol.breadcrumb").toHaveCount(1);
    expect(".o_breadcrumb span").toHaveCount(1);
    list.env.config.historyBack();
    await animationFrame();
    expect(".o_breadcrumb span").toHaveCount(1);
    expect(".o_breadcrumb").toHaveText("Partners Action 4", {
        message: "breadcrumbs should display the display_name of the action",
    });
});

test.tags("desktop");
test("stores and restores scroll position (in kanban)", async () => {
    defineActions([
        {
            id: 10,
            name: "Partners",
            res_model: "partner",
            views: [[false, "kanban"]],
        },
    ]);
    for (let i = 0; i < 60; i++) {
        Partner._records.push({ id: 100 + i, display_name: `Record ${i}` });
    }
    const container = document.createElement("div");
    container.classList.add("o_web_client");
    container.style.height = "250px";
    getFixture().appendChild(container);
    await mountWithCleanup(WebClient, { target: container });
    // execute a first action
    await getService("action").doAction(10);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    // simulate a scroll
    await scroll(".o_content", { top: 100 });
    // execute a second action (in which we don't scroll)
    await getService("action").doAction(4);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_content").toHaveProperty("scrollTop", 100);
});

test.tags("desktop");
test("stores and restores scroll position (in list)", async () => {
    for (let i = 0; i < 60; i++) {
        Partner._records.push({ id: 100 + i, display_name: `Record ${i}` });
    }
    const container = document.createElement("div");
    container.classList.add("o_web_client");
    container.style.height = "250px";
    getFixture().appendChild(container);
    await mountWithCleanup(WebClient, { target: container });
    // execute a first action
    await getService("action").doAction(3);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    expect(queryOne(".o_list_renderer").scrollTop).toBe(0);
    // simulate a scroll
    queryOne(".o_list_renderer").scrollTop = 100;
    // execute a second action (in which we don't scroll)
    await getService("action").doAction(4);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_content").toHaveProperty("scrollTop", 0);
    expect(queryOne(".o_list_renderer").scrollTop).toBe(100);
});

test.tags("desktop");
test('executing an action with target != "new" closes all dialogs', async () => {
    Partner._views["form"] = `
        <form>
            <field name="o2m">
                <list><field name="display_name"/></list>
                <form><field name="display_name"/></form>
            </field>
        </form>`;
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    await contains(".o_list_view .o_data_row .o_list_char").click();
    expect(".o_form_view").toHaveCount(1);
    await contains(".o_form_view .o_data_row .o_data_cell").click();
    expect(".modal .o_form_view").toHaveCount(1);
    await getService("action").doAction(1); // target != 'new'
    await animationFrame(); // wait for the dialog to be closed
    expect(".modal").toHaveCount(0);
});

test.tags("desktop");
test('executing an action with target "new" does not close dialogs', async () => {
    Partner._views["form"] = `
        <form>
            <field name="o2m">
                <list><field name="display_name"/></list>
                <form><field name="display_name"/></form>
            </field>
        </form>`;
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    await contains(".o_list_view .o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    await contains(".o_form_view .o_data_row .o_data_cell").click();
    expect(".modal .o_form_view").toHaveCount(1);
    await getService("action").doAction(5); // target 'new'
    expect(".modal .o_form_view").toHaveCount(2);
});

test.tags("desktop");
test("search defaults are removed from context when switching view", async () => {
    expect.assertions(1);
    const context = {
        search_default_x: true,
        searchpanel_default_y: true,
    };
    patchWithCleanup(PivotModel.prototype, {
        load(searchParams) {
            expect(searchParams.context).toEqual({
                allowed_company_ids: [1],
                lang: "en",
                tz: "taht",
                uid: 7,
            });
            return super.load(...arguments);
        },
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "pivot"],
        ],
        context,
    });
    // list view is loaded, switch to pivot view
    await switchView("pivot");
});

test("retrieving a stored action should remove 'allowed_company_ids' from its context (model)", async () => {
    // Prepare a multi company scenario
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];

    // Prepare a stored action
    browser.sessionStorage.setItem(
        "current_action",
        JSON.stringify({
            id: 1,
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "kanban"]],
            context: {
                someKey: 44,
                allowed_company_ids: [1, 2],
                lang: "not_en",
                tz: "not_taht",
                uid: 42,
            },
        })
    );

    // Prepare the URL hash to make sure the stored action will get executed.
    Object.assign(browser.location, { search: "?model=partner&view_type=kanban" });

    // Create the web client. It should execute the stored action.
    await mountWithCleanup(WebClient);
    await animationFrame(); // blank action

    // Check the current action context
    expect(getService("action").currentController.action.context).toEqual({
        // action context
        someKey: 44,
        lang: "not_en",
        tz: "not_taht",
        uid: 42,
        // note there is no 'allowed_company_ids' in the action context
    });
});

test("retrieving a stored action should remove 'allowed_company_ids' from its context (action)", async () => {
    // Prepare a multi company scenario
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];

    // Prepare a stored action
    browser.sessionStorage.setItem(
        "current_action",
        JSON.stringify({
            id: 1,
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "kanban"]],
            context: {
                someKey: 44,
                allowed_company_ids: [1, 2],
                lang: "not_en",
                tz: "not_taht",
                uid: 42,
            },
        })
    );

    // Prepare the URL hash to make sure the stored action will get executed.
    // Object.assign(browser.location, { search: "?model=partner&view_type=kanban" });
    redirect("/odoo/action-1?view_type=kanban");

    // Create the web client. It should execute the stored action.
    await mountWithCleanup(WebClient);
    await animationFrame(); // blank action

    // Check the current action context
    expect(getService("action").currentController.action.context).toEqual({
        // action context
        someKey: 44,
        lang: "not_en",
        tz: "not_taht",
        uid: 42,
        // note there is no 'allowed_company_ids' in the action context
    });
});
test.tags("desktop");
test("action is removed while waiting for another action with selectMenu", async () => {
    let def;
    class SlowClientAction extends Component {
        static template = xml`<div>My client action</div>`;
        static props = ["*"];

        setup() {
            onWillStart(() => def);
        }
    }
    actionRegistry.add("slow_client_action", SlowClientAction);
    defineActions([
        {
            id: 1001,
            tag: "slow_client_action",
            target: "main",
            type: "ir.actions.client",
            params: { description: "Id 1" },
        },
    ]);
    defineMenus([
        {
            id: 1,
            name: "App1",
            actionID: 1001,
            xmlid: "menu_1",
        },
    ]);

    await mountWithCleanup(WebClient);
    // starting point: a kanban view
    await getService("action").doAction(4);
    expect(".o_kanban_view").toHaveCount(1);

    // select app in navbar menu
    def = new Deferred();
    await contains(".o_navbar_apps_menu .dropdown-toggle").click();
    const appsMenu = getDropdownMenu(".o_navbar_apps_menu");
    await contains(".o_app:contains(App1)", { root: appsMenu }).click();

    // check that the action manager is empty, even though client action is loading
    expect(".o_action_manager").toHaveText("");

    // resolve onwillstart so client action is ready
    def.resolve();
    await animationFrame();
    expect(".o_action_manager").toHaveText("My client action");
});
