// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, runAllTimers } from "@odoo/hoot-dom";
import { animationFrame, Deferred, microTick } from "@odoo/hoot-mock";
import { Component, onWillStart, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    isItemSelected,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
    switchView,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
} from "@web/../tests/web_test_helpers";
import { useSetupAction } from "@web/core/action_hook";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { AppEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { SupersededError } from "@web/core/utils/concurrency";
import { redirect } from "@web/core/utils/urls";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchBar } from "@web/search/search_bar/search_bar";

const { ResCompany, ResPartner, ResUsers } = webModels;
const actionRegistry = registry.category("actions");

class Partner extends models.Model {
    _rec_name = "display_name";

    start = fields.Date();

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        form: `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                </header>
                <group>
                    <field name="display_name"/>
                </group>
            </form>
        `,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        list: `<list><field name="display_name"/></list>`,
        calendar: `<calendar date_start="start"/>`,
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

defineModels([Partner, Pony, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "calendar"],
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
]);

test("drop previous actions if possible", async () => {
    const def = new Deferred();
    stepAllNetworkCalls();
    onRpc("/web/action/load", () => def);

    await mountWebClient();
    getService("action").doAction(4);
    getService("action").doAction(8);
    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("handle switching view and switching back on slow network", async () => {
    const def = new Deferred();
    const defs = [null, def, null];
    stepAllNetworkCalls();
    onRpc("web_search_read", () => defs.shift());

    await mountWebClient();
    await getService("action").doAction(4);
    await switchView("list");
    await switchView("kanban");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_search_read",
    ]);

    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "there should be a kanban view in dom",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "there should not be a list view in dom",
    });
});

test.tags("desktop");
test("clicking quickly on breadcrumbs...", async () => {
    /** @type {any} */
    let def;
    onRpc("web_read", () => def);

    await mountWebClient();
    await getService("action").doAction(4);
    await contains(".o_kanban_record").click();
    await getService("action").doAction(8);

    def = new Deferred();
    await contains(queryAll(".o_control_panel .breadcrumb-item")[1]).click();
    await contains(".o_control_panel .breadcrumb-item").click();

    def.resolve();
    await animationFrame();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 4",
    ]);
});

test.tags("desktop");
test("execute a new action while loading a lazy-loaded controller", async () => {
    defineActions([
        {
            id: 77,
            type: "ir.actions.act_window",
            res_model: "partner",
            views: [
                [false, "calendar"],
                [false, "form"],
            ],
        },
    ]);
    redirect("/odoo/action-77/2?cids=1");

    /** @type {any} */
    let def;
    onRpc("partner", "search_read", () => def);
    stepAllNetworkCalls();

    await mountWebClient();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1, {
        message: "should display the form view of action 4",
    });

    def = new Deferred();
    await contains(".o_control_panel .breadcrumb a").click();
    expect(".o_form_view").toHaveCount(1, {
        message: "should still display the form view of action 4",
    });

    await getService("action").doAction(8, { clearBreadcrumbs: true });
    expect(".o_list_view").toHaveCount(1, { message: "should display action 8" });
    expect(".o_form_view").toHaveCount(0, {
        message: "should no longer display the form view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_read",
        "search_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);

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
            views: [[1, "kanban"]],
        };
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1, {
        message: "should display the form view of action 3",
    });

    await contains('.o_form_view button[name="object"]').click();
    expect(".o_form_view").toHaveCount(1, {
        message: "should still display the form view of action 3",
    });

    await getService("action").doAction(8, { clearBreadcrumbs: true });
    expect(".o_list_view").toHaveCount(1, {
        message: "should display the list view of action 8",
    });
    expect(".o_form_view").toHaveCount(0, {
        message: "should no longer display the form view",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "object",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);

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
    /** @type {any} */
    let def;
    stepAllNetworkCalls();
    onRpc("web_read", () => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1, {
        message: "should display the list view of action 3",
    });

    def = new Deferred();
    await contains(".o_list_view .o_data_cell").click();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still display the list view of action 3",
    });

    await getService("action").doAction(4, { clearBreadcrumbs: true });
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view of action 8",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "should no longer display the list view",
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

test.tags("desktop");
test("a navigation blocked in clearUncommittedChanges can't mount over a newer one", async () => {
    await mountWebClient();
    const am = getService("action");

    const saveDef = new Deferred();
    let armed = true;
    am.env.bus.addEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, (ev) => {
        if (armed) {
            armed = false;
            ev.detail.push(() => saveDef);
        }
    });

    const navA = am.doAction(8);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "A is blocked in clearUncommittedChanges, nothing mounted yet",
    });

    await am.doAction(4);
    expect(".o_kanban_view").toHaveCount(1, { message: "newer action B is shown" });

    saveDef.resolve(true);
    await navA;
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "B (newer) is still shown after A unblocks",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "A (older, superseded) never mounted",
    });
});

test.tags("desktop");
test("a switchView blocked in clearUncommittedChanges can't mount over a newer one", async () => {
    await mountWebClient();
    const am = getService("action");

    await am.doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "action 3 list is shown" });

    const saveDef = new Deferred();
    let armed = true;
    am.env.bus.addEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, (ev) => {
        if (armed) {
            armed = false;
            ev.detail.push(() => saveDef);
        }
    });

    const navA = am.switchView("calendar");
    await animationFrame();
    expect(".o_calendar_view").toHaveCount(0, {
        message: "A is blocked in clearUncommittedChanges, calendar not mounted",
    });

    await am.doAction(4);
    expect(".o_kanban_view").toHaveCount(1, { message: "newer action B is shown" });

    saveDef.resolve(true);
    await navA;
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "B (newer) is still shown after A unblocks",
    });
    expect(".o_calendar_view").toHaveCount(0, {
        message: "A (older, superseded) never mounted",
    });
});

test.tags("desktop");
test("a restore blocked in clearUncommittedChanges can't mount over a newer one", async () => {
    await mountWebClient();
    const am = getService("action");

    await am.doAction(3);
    await am.doAction(4);
    expect(".o_kanban_view").toHaveCount(1, { message: "action 4 kanban is shown" });
    const firstJsId = am.controllerStack[0].jsId;

    const saveDef = new Deferred();
    let armed = true;
    am.env.bus.addEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, (ev) => {
        if (armed) {
            armed = false;
            ev.detail.push(() => saveDef);
        }
    });

    const navA = am.restore(firstJsId);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "A is blocked in clearUncommittedChanges, list not mounted",
    });

    await am.doAction(4);
    expect(".o_kanban_view").toHaveCount(1, { message: "newer action B is shown" });

    saveDef.resolve(true);
    await navA;
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "B (newer) is still shown after A unblocks",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "A (older, superseded restore) never mounted",
    });
});

test.tags("desktop");
test("a client action blocked in clearUncommittedChanges can't mount over a newer one", async () => {
    class BlockedClientAction extends Component {
        static template = xml`<div class="blocked-client-action">A</div>`;
        static props = ["*"];
    }
    actionRegistry.add("blockedClientAction", BlockedClientAction);

    await mountWebClient();
    const am = getService("action");

    await am.doAction(3);
    expect(".o_list_view").toHaveCount(1, { message: "action 3 list is shown" });

    const saveDef = new Deferred();
    let armed = true;
    am.env.bus.addEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, (ev) => {
        if (armed) {
            armed = false;
            ev.detail.push(() => saveDef);
        }
    });

    const navA = am.doAction("blockedClientAction");
    await animationFrame();
    expect(".blocked-client-action").toHaveCount(0, {
        message: "A is blocked in clearUncommittedChanges, nothing mounted yet",
    });

    await am.doAction(4);
    expect(".o_kanban_view").toHaveCount(1, { message: "newer action B is shown" });

    saveDef.resolve(true);
    await navA;
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "B (newer) is still shown after A unblocks",
    });
    expect(".blocked-client-action").toHaveCount(0, {
        message: "A (older, superseded client action) never mounted",
    });
});

test("a loadState blocked reconstructing breadcrumbs can't commit over a newer one", async () => {
    await mountWebClient();
    const am = getService("action");

    const breadcrumbDef = new Deferred();
    let firstCall = true;
    patchWithCleanup(am, {
        async controllersFromState() {
            if (firstCall) {
                firstCall = false;
                await breadcrumbDef;
            }
            return [];
        },
    });

    const navA = am.loadState({ action: 3 }).catch((error) => error);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "A is blocked reconstructing breadcrumbs, nothing mounted yet",
    });

    await am.loadState({ action: 4 });
    expect(".o_kanban_view").toHaveCount(1, { message: "newer state B is shown" });

    breadcrumbDef.resolve();
    const resultA = await navA;
    await animationFrame();
    expect(resultA).toBeInstanceOf(SupersededError);
    expect(".o_kanban_view").toHaveCount(1, {
        message: "B (newer) is still shown after A unblocks",
    });
    expect(".o_list_view").toHaveCount(0, {
        message: "A (older, superseded loadState) never committed",
    });
});

test("execute a new action while loading views", async () => {
    const def = new Deferred();
    stepAllNetworkCalls();
    onRpc("get_views", () => def);

    await mountWebClient();
    getService("action").doAction(3);
    await animationFrame();
    expect(".o_list_view").toHaveCount(0, {
        message: "should not display the list view of action 3",
    });

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
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 4",
    ]);
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
    onRpc("web_read", () => def);

    await mountWebClient();
    getService("action").doAction({
        name: "A Partner",
        res_model: "partner",
        res_id: 1,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    await animationFrame();
    expect(".o_form_view").toHaveCount(0, {
        message: "should not display the form view",
    });

    getService("action").doAction(4);
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should display the kanban view of action 4",
    });
    expect(".o_form_view").toHaveCount(0, {
        message: "should not display the form view",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 4",
    ]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("open a record while reloading the list view", async () => {
    /** @type {any} */
    let def;
    onRpc("search_read", () => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_calendar_view").toHaveCount(0);
    expect(".o_list_view").toHaveCount(1);
    expect(".o_list_view .o_data_row").toHaveCount(2);
    expect(".o_control_panel .o_list_button_add").toHaveCount(1);

    def = new Deferred();
    await switchView("calendar");
    expect(".o_list_view .o_data_row").toHaveCount(2);
    expect(".o_control_panel .o_list_button_add").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_control_panel .o_list_button_add").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_list_view").toHaveCount(0);
    expect(".o_calendar_view").toHaveCount(0);
    expect(".o_control_panel .o_list_button_add").toHaveCount(0);
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

    await mountWebClient();
    getService("action").doAction("slowAction");
    await animationFrame();
    expect(".client_action").toHaveCount(0, {
        message: "client action isn't ready yet",
    });

    getService("action").doAction(4);
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should have loaded a kanban view",
    });

    slowWillStartDef.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1, {
        message: "should still display the kanban view",
    });
});

test.tags("desktop");
test("restoring a controller when doing an action -- load_action slow", async () => {
    /** @type {any} */
    let def;
    onRpc("/web/action/load", () => def);
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_list_view .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4, { clearBreadcrumbs: true });
    await animationFrame();
    expect(".o_form_view").toHaveCount(1, {
        message: "should still contain the form view",
    });

    await contains(".o_control_panel .breadcrumb-item a").click();
    def.resolve();
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "/web/action/load",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- load_action slow", async () => {
    /** @type {any} */
    let def;
    onRpc("/web/action/load", () => def);
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4, { clearBreadcrumbs: true });
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still contain the list view",
    });

    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "/web/action/load",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- get_views slow", async () => {
    /** @type {any} */
    let def;
    onRpc("get_views", () => def);
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    def = new Deferred();
    getService("action").doAction(4);
    await animationFrame();
    expect(".o_list_view").toHaveCount(1, {
        message: "should still contain the list view",
    });

    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("switching when doing an action -- search_read slow", async () => {
    const def = new Deferred();
    onRpc("search_read", () => def);
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "partner",
        views: [[false, "calendar"]],
    });
    await animationFrame();
    await switchView("kanban");
    def.resolve();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners",
    ]);
    expect(".o_list_view").toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "get_views",
        "search_read",
        "web_search_read",
    ]);
});

test.tags("desktop");
test("click multiple times to open a record", async () => {
    const def = new Deferred();
    onRpc("web_read", () => def);

    await mountWebClient();
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    const row1 = queryAll(".o_list_view .o_data_row")[0];
    const row2 = queryAll(".o_list_view .o_data_row")[1];
    await contains(row1.querySelector(".o_data_cell")).click();
    await contains(row2.querySelector(".o_data_cell")).click();

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

    await mountWebClient();
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
        toy: `<toy/>`,
        list: `<list><field name="display_name"/></list>`,
        search: `<search><filter name="display_name" string="Foo" domain="[]"/></search>`,
    };

    /** @type {Promise<void> | InstanceType<typeof Deferred>} */
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
            expect.step(this.props.state || "no state");
            useSetupAction({
                getLocalState: () => ({ fromId: this.id }),
            });
            onWillStart(() => def);
        }
    }

    registry.category("views").add("toy", {
        type: "toy",
        Controller: ToyController,
    });

    await mountWebClient();

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "toy"],
            [false, "list"],
        ],
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(isItemSelected("Foo")).toBe(true);

    const transition = new Deferred();
    def = transition;
    await contains(".o_control_panel .o_switch_view.o_toy").click();
    await contains(".o_control_panel .o_switch_view.o_toy").click();

    transition.resolve();
    await animationFrame();

    await toggleSearchBarMenu();
    expect(isItemSelected("Foo")).toBe(true);

    expect.verifySteps(["no state", { fromId: 1 }, { fromId: 1 }]);
});

test.tags("desktop");
test("doing browser back navigates to the previous action", async () => {
    /** @type {any} */
    let def;
    onRpc("partner", "web_search_read", () => def);
    await mountWebClient();

    await getService("action").doAction(4);
    await getService("action").doAction(8);
    await runAllTimers();
    expect(router.current).toEqual({
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

    def = new Deferred();
    browser.history.back();
    expect(document.body.style.pointerEvents).not.toBe("none");
    def.resolve();

    await animationFrame();
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 4",
    ]);
});

test.tags("desktop");
test("superseded clearBreadcrumbs skeleton wait doesn't leave doAction pending", async () => {
    class ClientActionA extends Component {
        static template = xml`<div class="client-a">A</div>`;
        static props = ["*"];
    }
    class ClientActionB extends Component {
        static template = xml`<div class="client-b">B</div>`;
        static props = ["*"];
    }
    actionRegistry.add("clientA", ClientActionA);
    actionRegistry.add("clientB", ClientActionB);

    await mountWebClient();
    const action = getService("action");

    let skeletonsPosted = 0;
    action.env.bus.addEventListener(AppEvent.ACTION_MANAGER_UPDATE, (ev) => {
        if (ev.detail?.Component?.name === "SkeletonView") {
            skeletonsPosted++;
        }
    });

    let aSettled = false;
    let aError = null;
    action.doAction("clientA", { clearBreadcrumbs: true }).then(
        () => {
            aSettled = true;
        },
        (err) => {
            aSettled = true;
            aError = err;
        },
    );
    for (let i = 0; i < 50 && !skeletonsPosted; i++) {
        await microTick();
    }
    expect(skeletonsPosted).toBe(1, {
        message: "A is parked on its skeleton wait, nothing mounted yet",
    });

    action.doAction("clientB", { clearBreadcrumbs: true });
    for (let i = 0; i < 50 && !aSettled; i++) {
        await animationFrame();
    }
    expect(aSettled).toBe(true);
    expect(aError).toBe(null);

    await animationFrame();
    await animationFrame();
    expect(".client-b").toHaveCount(1);
    expect(".client-a").toHaveCount(0);
    expect(".o_skeleton_view").toHaveCount(0);
    expect.verifySteps([]);
});
