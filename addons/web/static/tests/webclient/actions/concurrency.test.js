import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, onWillStart, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    isItemSelected,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
    switchView,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
} from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSetupAction } from "@web/search/action_hook";
import { WebClient } from "@web/webclient/webclient";

const { ResCompany, ResPartner, ResUsers } = webModels;
const actionRegistry = registry.category("actions");

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        "form,false": `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
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
        "list,false": `<list><field name="display_name"/></list>`,
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
        "list,false": `<list><field name="name"/></list>`,
        "form,false": `<form><field name="name"/></form>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner, Pony, ResCompany, ResPartner, ResUsers]);

defineActions([
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
            [2, "list"],
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
]);

test("drop previous actions if possible", async () => {
    const def = new Deferred();
    stepAllNetworkCalls();
    onRpc("/web/action/load", () => def);

    await mountWithCleanup(WebClient);
    getService("action").doAction(4);
    getService("action").doAction(8);
    def.resolve();
    await animationFrame();
    // action 4 loads a kanban view first, 6 loads a list view. We want a list
    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test.tags("desktop");
test("handle switching view and switching back on slow network", async () => {
    const def = new Deferred();
    const defs = [null, def, null];
    stepAllNetworkCalls();
    onRpc("web_search_read", () => defs.shift());

    await mountWithCleanup(WebClient);
    await getService("action").doAction(4);
    // kanban view is loaded, switch to list view
    await switchView("list");
    // here, list view is not ready yet, because def is not resolved
    // switch back to kanban view
    await switchView("kanban");
    // here, we want the kanban view to reload itself, regardless of list view
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_search_read",
        "has_group",
        "web_search_read",
    ]);

    // we resolve def => list view is now ready (but we want to ignore it)
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, { message: "there should be a kanban view in dom" });
    expect(".o_list_view").toHaveCount(0, { message: "there should not be a list view in dom" });
});

test.tags("desktop");
test("clicking quickly on breadcrumbs...", async () => {
    let def;
    onRpc("web_read", () => def);

    await mountWithCleanup(WebClient);
    // create a situation with 3 breadcrumbs: kanban/form/list
    await getService("action").doAction(4);
    await contains(".o_kanban_record").click();
    await getService("action").doAction(8);

    // now, the next read operations will be promise (this is the read
    // operation for the form view reload)
    def = new Deferred();
    // click on the breadcrumbs for the form view, then on the kanban view
    // before the form view is fully reloaded
    await contains(queryAll(".o_control_panel .breadcrumb-item")[1]).click();
    await contains(".o_control_panel .breadcrumb-item").click();

    // resolve the form view read
    def.resolve();
    await animationFrame();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners Action 4"]);
});

test.tags("desktop");
test("execute a new action while loading a lazy-loaded controller", async () => {
    redirect("/odoo/action-4/2?cids=1");

    let def;
    onRpc("partner", "web_search_read", () => def);
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await animationFrame(); // blank component
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view of action 4" });

    // click to go back to Kanban (this request is blocked)
    def = new Deferred();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view").toHaveCount(1, {
        message: "should still display the form view of action 4",
    });

    // execute another action meanwhile (don't block this request)
    await getService("action").doAction(8, { clearBreadcrumbs: true });
    expect(".o_list_view").toHaveCount(1, { message: "should display action 8" });
    expect(".o_form_view").toHaveCount(0, { message: "should no longer display the form view" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read",
        "web_search_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    // unblock the switch to Kanban in action 4
    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, { message: "should still display action 8" });
    expect(".o_kanban_view").toHaveCount(0, {
        message: "should not display the kanban view of action 4",
    });
    expect.verifySteps([]);
});

test.tags("desktop");
test("execute a new action while handling a call_button", async () => {
    const def = new Deferred();
    onRpc("/web/dataset/call_button/*", async () => {
        await def;
        return {
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "kanban"]],
        };
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    // execute action 3 and open a record in form view
    await getService("action").doAction(3);
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, { message: "should display the form view of action 3" });

    // click on 'Call method' button (this request is blocked)
    await contains('.o_form_view button[name="object"]').click();
    expect(".o_form_view").toHaveCount(1, {
        message: "should still display the form view of action 3",
    });

    // execute another action
    await getService("action").doAction(8, { clearBreadcrumbs: true });
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view of action 8" });
    expect(".o_form_view").toHaveCount(0, { message: "should no longer display the form view" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "web_read",
        "object",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);

    // unblock the call_button request
    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view of action 8",
    });
    expect(".o_kanban_view").toHaveCount(0, { message: "should not display action 1" });
    expect.verifySteps([]);
});

test.tags("desktop");
test("execute a new action while switching to another controller", async () => {
    // This test's bottom line is that a doAction always has priority
    // over a switch controller (clicking on a record row to go to form view).
    // In general, the last actionManager's operation has priority because we want
    // to allow the user to make mistakes, or to rapidly reconsider her next action.
    // Here we assert that the actionManager's RPC are in order, but a 'read' operation
    // is expected, with the current implementation, to take place when switching to the form view.
    // Ultimately the form view's 'read' is superfluous, but can happen at any point of the flow,
    // except at the very end, which should always be the final action's list's 'search_read'.
    let def;
    stepAllNetworkCalls();
    onRpc("web_read", () => def);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "should display the list view of action 3" });

    // switch to the form view (this request is blocked)
    def = new Deferred();
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view of action 3",
    });

    // execute another action meanwhile (don't block this request)
    await getService("action").doAction(4, { clearBreadcrumbs: true });
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view of action 8",
    });
    expect(".o_list_view").toHaveCount(0, { message: "should no longer display the list view" });
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

    // unblock the switch to the form view in action 3
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should still display the kanban view of action 8",
    });
    expect(".o_form_view").toHaveCount(0, {
        message: "should not display the form view of action 3",
    });
    expect.verifySteps([]);
});

test("execute a new action while loading views", async () => {
    const def = new Deferred();
    stepAllNetworkCalls();
    onRpc("get_views", () => def);

    await mountWithCleanup(WebClient);
    // execute a first action (its 'get_views' RPC is blocked)
    getService("action").doAction(3);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "should not display the list view of action 3",
    });

    // execute another action meanwhile (and unlock the RPC)
    getService("action").doAction(4);
    await animationFrame();
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view of action 4",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "should not display the list view of action 3",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners Action 4"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("execute a new action while loading data of default view", async () => {
    const def = new Deferred();
    stepAllNetworkCalls();
    onRpc("web_search_read", () => def);

    await mountWithCleanup(WebClient);
    // execute a first action (its 'search_read' RPC is blocked)
    getService("action").doAction(3);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "should not display the list view of action 3",
    });

    // execute another action meanwhile (and unlock the RPC)
    getService("action").doAction(4);
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view of action 4",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "should not display the list view of action 3",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners Action 4"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("open a record while reloading the list view", async () => {
    let def;
    onRpc("web_search_read", () => def);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(2);
    expect(".o_control_panel .o_list_buttons").toHaveCount(1);

    // reload (the search_read RPC will be blocked)
    def = new Deferred();
    await switchView("list");
    expect(".o_list_view .o_data_row").toHaveCount(2);
    expect(".o_control_panel .o_list_buttons").toHaveCount(1);

    // open a record in form view
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_control_panel .o_list_buttons").toHaveCount(0);

    // unblock the search_read RPC
    def.resolve();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_list_view").toHaveCount(0);
    expect(".o_control_panel .o_list_buttons").toHaveCount(0);
});

test("properly drop client actions after new action is initiated", async () => {
    const slowWillStartDef = new Deferred();
    class ClientAction extends Component {
        static template = xml`<div class="client_action">ClientAction</div>`;
        static props = ["*"];
        setup() {
            onWillStart(() => slowWillStartDef);
        }
    }
    actionRegistry.add("slowAction", ClientAction);

    await mountWithCleanup(WebClient);
    getService("action").doAction("slowAction");
    await animationFrame();
    expect(".client_action").toHaveCount(0, { message: "client action isn't ready yet" });

    getService("action").doAction(4);
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, { message: "should have loaded a kanban view" });

    slowWillStartDef.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, { message: "should still display the kanban view" });
});

test.tags("desktop");
test("restoring a controller when doing an action -- load_action slow", async () => {
    let def;
    onRpc("/web/action/load", () => def);
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4, { clearBreadcrumbs: true });
    await animationFrame();
    expect(".o_form_view").toHaveCount(1, { message: "should still contain the form view" });

    await contains(".o_control_panel .breadcrumb-item a").click();
    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "web_read",
        "/web/action/load",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- load_action slow", async () => {
    let def;
    onRpc("/web/action/load", () => def);
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4, { clearBreadcrumbs: true });
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, { message: "should still contain the list view" });

    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "/web/action/load",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- get_views slow", async () => {
    let def;
    onRpc("get_views", () => def);
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4);
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, { message: "should still contain the list view" });

    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- search_read slow", async () => {
    const def = new Deferred();
    const defs = [null, def, null];
    onRpc("web_search_read", () => defs.shift());
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    getService("action").doAction(4);
    await animationFrame();
    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Partners"]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("click multiple times to open a record", async () => {
    const def = new Deferred();
    const defs = [null, def];
    onRpc("web_read", () => defs.shift());

    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_back_button").click();
    expect(".o_list_view").toHaveCount(1);

    const row1 = queryAll(".o_list_view .o_data_row")[0];
    const row2 = queryAll(".o_list_view .o_data_row")[1];
    await contains(row1.querySelector(".o_data_cell")).click();
    await contains(row2.querySelector(".o_data_cell")).click();
    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "Second record",
    ]);

    def.resolve();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
        "Second record",
    ]);
});

test("dialog will only open once for two rapid actions with the target new", async () => {
    const def = new Deferred();
    onRpc("onchange", () => def);

    await mountWithCleanup(WebClient);
    getService("action").doAction(5);
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(0);

    getService("action").doAction(5);
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
});

test.tags("desktop");
test("local state, global state, and race conditions", async () => {
    patchWithCleanup(serverState.view_info, {
        toy: { multi_record: true, display_name: "Toy", icon: "fab fa-android" },
    });
    Partner._views = {
        "toy,false": `<toy/>`,
        "list,false": `<list><field name="display_name"/></list>`,
        "search,false": `<search><filter name="display_name" string="Foo" domain="[]"/></search>`,
    };

    let def = Promise.resolve();
    let id = 1;
    class ToyController extends Component {
        static template = xml`
            <div class="o_toy_view">
                <ControlPanel />
                <SearchBar />
            </div>`;
        static components = { ControlPanel, SearchBar };
        static props = ["*"];
        setup() {
            this.id = id++;
            expect.step(JSON.stringify(this.props.state || "no state"));
            useSetupAction({
                getLocalState: () => {
                    return { fromId: this.id };
                },
            });
            onWillStart(() => def);
        }
    }

    registry.category("views").add("toy", {
        type: "toy",
        Controller: ToyController,
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        // list (or something else) must be added to have the view switcher displayed
        views: [
            [false, "toy"],
            [false, "list"],
        ],
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(isItemSelected("Foo")).toBe(true);

    // reload twice by clicking on toy view switcher
    def = new Deferred();
    await contains(".o_control_panel .o_switch_view.o_toy").click();
    await contains(".o_control_panel .o_switch_view.o_toy").click();

    def.resolve();
    await animationFrame();

    await toggleSearchBarMenu();
    expect(isItemSelected("Foo")).toBe(true);
    // this test is not able to detect that getGlobalState is put on the right place:
    // currentController.action.globalState contains in any case the search state
    // of the first instantiated toy view.

    expect.verifySteps([
        `"no state"`, // setup first view instantiated
        `{"fromId":1}`, // setup second view instantiated
        `{"fromId":1}`, // setup third view instantiated
    ]);
});
