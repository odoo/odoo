import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne, scroll } from "@odoo/hoot-dom";
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
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    switchView,
    webModels,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import { listView } from "@web/views/list/list_view";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { WebClient } from "@web/webclient/webclient";

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
        "form,false": `
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
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<tree><field name="display_name"/></tree>`,
        "list,2": `<tree limit="3"><field name="display_name"/></tree>`,
        "search,false": `<search/>`,
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
        "list,false": '<tree><field name="name"/></tree>',
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
        id: 5,
        xml_id: "action_5",
        name: "Create a Partner",
        res_model: "partner",
        target: "new",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        type: "ir.actions.act_window",
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
        type: "ir.actions.act_window",
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
            id: 1,
            tag: "client_action_by_db_id",
            target: "main",
            type: "ir.actions.client",
        },
        {
            id: 2,
            xml_id: "some_action",
            tag: "client_action_by_xml_id",
            target: "main",
            type: "ir.actions.client",
        },
        {
            id: 3,
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
    await getService("action").doAction(1);
    expect(["client_action_db_id"]).toVerifySteps();
    await getService("action").doAction("some_action");
    expect(["client_action_xml_id"]).toVerifySteps();
    await getService("action").doAction("my_action");
    expect(["client_action_path"]).toVerifySteps();
    await getService("action").doAction("client_action_by_tag");
    expect(["client_action_tag"]).toVerifySteps();
    await getService("action").doAction({
        tag: "client_action_by_object",
        target: "current",
        type: "ir.actions.client",
    });
    expect(["client_action_object"]).toVerifySteps();
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
    expect(["ir.action_in_handler_registry"]).toVerifySteps();
});

test("properly handle case when action id does not exist", async () => {
    expect.assertions(2);
    patchWithCleanup(console, {
        warn: () => {},
    });
    mockService("notification", () => {
        return {
            add(message) {
                expect(message).toBe("No action with id '4448' could be found");
            },
        };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(4448);
    expect("div.o_invalid_action").toHaveCount(1);
});

test("actions can be cached", async () => {
    onRpc("/web/action/load", async (request) => {
        const { params } = await request.json();
        expect.step(JSON.stringify(params));
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

    expect(
        [
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"configuratorMode":"add"}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"configuratorMode":"edit"}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_id":1}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_id":2}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_ids":[1,2]}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_ids":[1,2,3]}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_model":"a"}}',
            '{"action_id":3,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_model":"b"}}',
        ],
        "should load from server once per active_id/active_ids/active_model change, nothing else"
    ).toVerifySteps();
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
    expect(["server loaded"]).toVerifySteps();
    expect(action.context).toEqual(actionParams);

    // Modify the action in place
    action.context.additionalContext.some.deep.nested = "Nesta";

    // Change additionalContext and reload
    actionParams.additionalContext.some.deep.nested = "Marley";
    action = await getService("action").loadAction(3, actionParams);
    expect(["server loaded"]).toVerifySteps();
    expect(action.context).toEqual(actionParams);
});

test('action with "no_breadcrumbs" set to true', async () => {
    defineActions([
        {
            id: 42,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "kanban"]],
            context: { no_breadcrumbs: true },
        },
    ]);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_control_panel .o_breadcrumb").toHaveCount(1);
    // push another action flagged with 'no_breadcrumbs=true'
    await getService("action").doAction(42);
    expect(".o_control_panel .o_breadcrumb").toHaveCount(0);
});

test("document's title is updated when an action is executed", async () => {
    await mountWithCleanup(WebClient);
    await animationFrame();
    let currentTitle = getService("title").getParts();
    expect(currentTitle).toEqual({});
    let currentState = router.current;
    expect(currentState).toEqual({ cids: 1 });
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
        cids: 1,
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
        cids: 1,
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
        cids: 1,
    });
});

test.tags("desktop")('handles "history_back" event', async () => {
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
    expect(".o_control_panel .o_breadcrumb").toHaveText("Partners Action 4", {
        message: "breadcrumbs should display the display_name of the action",
    });
});

test.tags("desktop")("stores and restores scroll position (in kanban)", async () => {
    defineActions([
        {
            id: 3,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
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
    await getService("action").doAction(3);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    // simulate a scroll
    scroll(".o_content", { top: 100 });
    // execute a second action (in which we don't scroll)
    await getService("action").doAction(4);
    expect(".o_content").toHaveProperty("scrollTop", 0);
    // go back using the breadcrumbs
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_content").toHaveProperty("scrollTop", 100);
});

test.tags("desktop")("stores and restores scroll position (in list)", async () => {
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

test.tags("desktop")('executing an action with target != "new" closes all dialogs', async () => {
    Partner._views["form,false"] = `
        <form>
            <field name="o2m">
                <tree><field name="display_name"/></tree>
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

test.tags("desktop")('executing an action with target "new" does not close dialogs', async () => {
    Partner._views["form,false"] = `
        <form>
            <field name="o2m">
                <tree><field name="display_name"/></tree>
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

test.tags("desktop")("search defaults are removed from context when switching view", async () => {
    expect.assertions(1);
    Partner._views["pivot,false"] = `<pivot/>`;
    Partner._views["list,false"] = `<list/>`;
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

test("retrieving a stored action should remove 'allowed_company_ids' from its context", async () => {
    // Prepare a multi company scenario
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];

    const action = {
        id: 1,
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    };

    // Prepare a stored action
    browser.sessionStorage.setItem(
        "current_action",
        JSON.stringify({
            ...action,
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
    defineMenus([{ id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" }]);

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
