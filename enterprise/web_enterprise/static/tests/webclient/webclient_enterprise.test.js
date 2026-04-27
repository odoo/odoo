import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, keyDown, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockMatchMedia } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    clearRegistry,
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    getMockEnv,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { config as transitionConfig } from "@web/core/transition";
import { user } from "@web/core/user";
import { redirect } from "@web/core/utils/urls";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { shareUrlMenuItem } from "@web_enterprise/webclient/share_url/share_url";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

const actionRegistry = registry.category("actions");

/**
 * @param {{ env: import("@web/env").OdooEnv }} [options]
 */
async function mountWebClientEnterprise(options) {
    await mountWithCleanup(WebClientEnterprise, options);
    // Wait for visual changes caused by a potential loadState
    await animationFrame();
    // wait for BlankComponent
    await animationFrame();
    // wait for the regular rendering
    await animationFrame();
}

async function goToHomeMenu() {
    await click(".o_menu_toggle");
    await animationFrame();

    if (getMockEnv().isSmall) {
        await click(queryFirst(".o_sidebar_topbar a.btn-primary", { root: document.body }));
        await animationFrame();
    }
}

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[false, "kanban"]],
    },
    {
        id: 2,
        xml_id: "action_2",
        type: "ir.actions.server",
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        views: [
            [false, "kanban"],
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
        id: 6,
        xml_id: "action_6",
        name: "Partner",
        res_id: 2,
        res_model: "partner",
        target: "inline",
        views: [[false, "form"]],
    },
    {
        id: 1001,
        tag: "__test__client__action__",
        target: "main",
        type: "ir.actions.client",
        params: { description: "Id 1" },
    },
    {
        id: 1002,
        tag: "__test__client__action__",
        target: "main",
        type: "ir.actions.client",
        params: { description: "Id 2" },
    },
]);

defineMenus([
    { id: 0 }, // prevents auto-loading the first action
    { id: 1, name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
    { id: 2, name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
]);
class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });
    child_ids = fields.One2many({ relation: "partner", relation_field: "parent_id" });

    _records = [
        { id: 1, name: "First record", foo: "yop", parent_id: 3 },
        { id: 2, name: "Second record", foo: "blip", parent_id: 3 },
        { id: 3, name: "Third record", foo: "gnap", parent_id: 1 },
        { id: 4, name: "Fourth record", foo: "plop", parent_id: 1 },
        { id: 5, name: "Fifth record", foo: "zoup", parent_id: 1 },
    ];
    _views = {
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `<list><field name="foo"/></list>`,
        form: `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="name"/>
                    <field name="foo"/>
                </group>
            </form>
        `,
        search: `<search><field name="foo" string="Foo"/></search>`,
    };
}
defineModels([Partner]);
class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction_<t t-esc="props.action.params?.description"/>
        </div>
    `;
    static props = ["*"];

    setup() {
        onMounted(() => {
            this.env.config.setDisplayName(`Client action ${this.props.action.id}`);
        });
    }
}

onRpc("has_group", () => true);

beforeEach(() => {
    actionRegistry.add("__test__client__action__", TestClientAction);
    patchWithCleanup(transitionConfig, { disabled: true });
});
// Should test ONLY the webClient and features present in Enterprise
// Those tests rely on hidden view to be in CSS: display: none
describe("basic flow with home menu", () => {
    stepAllNetworkCalls();
    onRpc("partner", "get_formview_action", () => ({
        type: "ir.actions.act_window",
        res_model: "partner",
        view_type: "form",
        view_mode: "form",
        views: [[false, "form"]],
        target: "current",
        res_id: 2,
    }));
    defineMenus(
        [
            {
                id: 1,
                name: "App1",
                appID: 1,
                actionID: 4,
                xmlid: "menu_1",
            },
        ],
        { mode: "replace" }
    );
    test("1 -- start up", async () => {
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        expect(document.body).toHaveClass("o_home_menu_background");
        expect(".o_home_menu").toHaveCount(1);
        expect(".o_menu_toggle").not.toBeVisible();
        expect(".o_app.o_menuitem").toHaveCount(1);
    });

    test("2 -- navbar updates on displaying an action", async () => {
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        await contains(".o_app.o_menuitem").click();
        await animationFrame();
        expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
        expect(document.body).not.toHaveClass("o_home_menu_background");
        expect(".o_home_menu").toHaveCount(0);
        expect(".o_kanban_view").toHaveCount(1);
        expect(".o_menu_toggle").toBeVisible();
        expect(".o_menu_toggle").not.toHaveClass("o_menu_toggle_back");
    });

    test("3 -- push another action in the breadcrumb", async () => {
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        await contains(".o_app.o_menuitem").click();
        await animationFrame();
        expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
        expect(".o_kanban_view").toHaveCount(1);
        await contains(".o_kanban_record").click();
        await animationFrame(); // there is another tick to update navbar and destroy HomeMenu
        expect.verifySteps(["web_read"]);
        expect(".o_menu_toggle").toBeVisible();
        expect(".o_form_view").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("First record");
    });

    test.tags("desktop");
    test("4 -- push a third action in the breadcrumb", async () => {
        Partner._views["form"] = `
            <form>
                <field name="display_name"/>
                <field name="parent_id" open_target="current"/>
            </form>
        `;
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        await contains(".o_app.o_menuitem").click();
        await animationFrame();
        expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
        expect(".o_kanban_view").toHaveCount(1);
        await contains(".o_kanban_record").click();
        expect.verifySteps(["web_read"]);
        await contains('.o_field_widget[name="parent_id"] .o_external_button', {
            visible: false,
        }).click();
        expect.verifySteps(["get_formview_action", "get_views", "web_read"]);
        expect(".o_form_view").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Second record");
        // The third one is the active one
        expect(".breadcrumb-item").toHaveCount(2);
    });

    test("5 -- switch to HomeMenu from an action with 2 breadcrumbs", async () => {
        Partner._views["form"] = `
            <form>
                <field name="display_name"/>
                <field name="parent_id" open_target="current"/>
            </form>
        `;
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        await contains(".o_app.o_menuitem").click();
        await animationFrame();
        expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
        expect(".o_kanban_view").toHaveCount(1);
        await contains(".o_kanban_record").click();
        expect.verifySteps(["web_read"]);
        await contains('.o_field_widget[name="parent_id"] .o_external_button', {
            visible: false,
        }).click();
        expect.verifySteps(["get_formview_action", "get_views", "web_read"]);
        await goToHomeMenu();
        expect.verifySteps([]);
        expect(".o_menu_toggle").toHaveClass("o_menu_toggle_back");
        expect(".o_home_menu").toHaveCount(1);
        expect(".o_form_view").not.toHaveCount();
    });

    test.tags("desktop");
    test("6 -- back to underlying action with many breadcrumbs", async () => {
        Partner._views["form"] = `
            <form>
                <field name="display_name"/>
                <field name="parent_id" open_target="current"/>
            </form>
        `;
        await mountWebClientEnterprise();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        await contains(".o_app.o_menuitem").click();
        await animationFrame();
        expect.verifySteps(["/web/action/load", "get_views", "web_search_read"]);
        expect(".o_kanban_view").toHaveCount(1);
        await contains(".o_kanban_record").click();
        expect.verifySteps(["web_read"]);
        await contains('.o_field_widget[name="parent_id"] .o_external_button', {
            visible: false,
        }).click();
        expect.verifySteps(["get_formview_action", "get_views", "web_read"]);
        await contains(".o_menu_toggle").click();

        // can't click again too soon because of the mutex in home_menu
        // service (waiting for the url to be updated)
        await animationFrame();

        await contains(".o_menu_toggle").click();

        expect.verifySteps(["web_read"]);
        expect(".o_home_menu").toHaveCount(0);
        expect(".o_form_view").toHaveCount(1);
        expect(".o_menu_toggle").not.toHaveClass("o_menu_toggle_back");
        expect(".o_breadcrumb .active").toHaveText("Second record");
        // Third breadcrumb is the active one
        expect(".breadcrumb-item").toHaveCount(2);
    });
});

test("restore the newly created record in form view", async () => {
    defineActions(
        [
            {
                id: 6,
                xml_id: "action_6",
                name: "Partner",
                res_model: "partner",
                views: [[false, "form"]],
            },
        ],
        { mode: "replace" }
    );
    await mountWebClientEnterprise();

    await getService("action").doAction(6);
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    await contains(".o_field_widget[name=name] input").edit("red right hand");
    await contains(".o_form_button_save").click();
    expect(".o_breadcrumb .active").toHaveText("red right hand");
    await goToHomeMenu();
    expect(".o_form_view").not.toHaveCount();

    // can't click again too soon because of the mutex in home_menu
    // service (waiting for the url to be updated)
    await animationFrame();

    await contains(".o_menu_toggle").click();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_form_view .o_form_saved").toHaveCount(1);
    expect(".o_breadcrumb .active").toHaveText("red right hand");
});

test.tags("desktop");
test("fast clicking on restore (implementation detail)", async () => {
    expect.assertions(8);

    let doVeryFastClick = false;

    class DelayedClientAction extends Component {
        static template = xml`<div class='delayed_client_action'>
            <button t-on-click="resolve">RESOLVE</button>
        </div>`;
        static props = ["*"];
        setup() {
            onMounted(() => {
                if (doVeryFastClick) {
                    doVeryFastClick = false;
                    click(".o_menu_toggle"); //  go to home menu
                }
            });
        }
    }

    registry.category("actions").add("DelayedClientAction", DelayedClientAction);
    await mountWebClientEnterprise();
    await getService("action").doAction("DelayedClientAction");
    await animationFrame();
    await contains(".o_menu_toggle").click(); // go to home menu
    expect(".o_home_menu").toBeVisible();
    expect(".delayed_client_action").not.toHaveCount();

    doVeryFastClick = true;
    await contains(".o_menu_toggle").click(); // back
    expect(".o_home_menu").toHaveCount(0);
    expect(".delayed_client_action").toHaveCount(1);
    await animationFrame(); // waiting for DelayedClientAction
    expect(".o_home_menu").toBeVisible();
    expect(".delayed_client_action").not.toHaveCount();

    await contains(".o_menu_toggle").click(); // back
    await animationFrame();
    expect(".o_home_menu").toHaveCount(0);
    expect(".delayed_client_action").toHaveCount(1);
});

test("clear unCommittedChanges when toggling home menu", async () => {
    expect.assertions(6);
    // Edit a form view, don't save, toggle home menu
    // the autosave feature of the Form view is activated
    // and relied upon by this test

    onRpc("web_save", ({ args, model }) => {
        expect(model).toBe("partner");
        expect(args[1]).toEqual({
            name: "red right hand",
            foo: false,
        });
    });

    await mountWebClientEnterprise();
    await getService("action").doAction(3, { viewType: "form" });
    expect(".o_form_view .o_form_editable").toHaveCount(1);
    await contains(".o_field_widget[name=name] input").edit("red right hand");

    await goToHomeMenu();
    expect(".o_form_view").toHaveCount(0);
    expect(".modal").toHaveCount(0);
    expect(".o_home_menu").toHaveCount(1);
});

test("can have HomeMenu and dialog action", async () => {
    await mountWebClientEnterprise();
    expect(".o_home_menu").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(0);
    await getService("action").doAction(5);
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_form_view").toBeVisible();
    expect(".o_home_menu").toHaveCount(1);
});

test("supports attachments of apps deleted", async () => {
    // When doing a pg_restore without the filestore
    // LPE fixme: may not be necessary anymore since menus are not HomeMenu props anymore
    defineMenus([
        {
            id: 1,
            appID: 1,
            actionID: 1,
            xmlid: "",
            name: "Partners",
            webIconData: "",
            webIcon: "bloop,bloop",
        },
    ]);
    serverState.debug = "1";
    await mountWebClientEnterprise();
    expect(".o_home_menu").toHaveCount(1);
});

test.tags("desktop");
test("debug manager resets to global items when home menu is displayed", async () => {
    const debugRegistry = registry.category("debug");
    debugRegistry.category("default").add("item_1", () => ({
        type: "item",
        description: "globalItem",
        callback: () => {},
        sequence: 10,
    }));
    onRpc("has_access", () => true);
    serverState.debug = "1";
    await mountWebClientEnterprise();
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".dropdown-item:contains('globalItem')").toHaveCount(1);
    expect(".dropdown-item:contains('View: Kanban')").toHaveCount(0);

    await contains(".o_debug_manager .dropdown-toggle").click();
    await getService("action").doAction(1);
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".dropdown-item:contains('globalItem')").toHaveCount(1);
    expect(".dropdown-item:contains('View: Kanban')").toHaveCount(1);

    await contains(".o_menu_toggle").click();
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".dropdown-item:contains('globalItem')").toHaveCount(1);
    expect(".dropdown-item:contains('View: Kanban')").toHaveCount(0);

    await contains(".o_debug_manager .dropdown-toggle").click();
    await getService("action").doAction(3);
    await contains(".o_debug_manager .dropdown-toggle").click();
    expect(".dropdown-item:contains('globalItem')").toHaveCount(1);
    expect(".dropdown-item:contains('View: List')").toHaveCount(1);
    expect(".dropdown-item:contains('View: Kanban')").toHaveCount(0);
});

test("url state is well handled when going in and out of the HomeMenu", async () => {
    patchWithCleanup(browser.location, {
        origin: "http://example.com",
    });
    redirect("/odoo");
    await mountWebClientEnterprise();
    expect(router.current).toEqual({
        action: "menu",
        actionStack: [
            {
                action: "menu",
                displayName: "Home",
            },
        ],
    });
    expect(browser.history.length).toBe(1);

    await contains(".o_apps > .o_draggable:eq(1) > .o_app").click();
    await animationFrame();
    expect(router.current).toEqual({
        action: 1002,
        actionStack: [
            {
                action: 1002,
                displayName: "Client action 1002",
            },
        ],
    });
    expect(browser.history.length).toBe(2);
    expect(browser.location.href).toBe("http://example.com/odoo/action-1002");

    await goToHomeMenu();
    await animationFrame();
    expect(router.current).toEqual(
        {
            action: "menu",
            actionStack: [
                {
                    action: 1002,
                    displayName: "Client action 1002",
                },
                {
                    action: "menu",
                    displayName: "Home",
                },
            ],
        },
        {
            message:
                "the actionStack is required to be able to restore the menu toggle back button and the underlying breadcrumbs",
        }
    );
    expect(browser.history.length).toBe(3);
    expect(browser.location.href).toBe("http://example.com/odoo", {
        message:
            "despite the actionStack being in the router state, the url shouldn't have any path",
    });

    await contains(".o_apps > .o_draggable:eq(0) > .o_app").click();
    await animationFrame();
    expect(router.current).toEqual(
        {
            action: 1001,
            actionStack: [
                {
                    action: 1001,
                    displayName: "Client action 1001",
                },
            ],
        },
        { message: "clicking another app creates a new action stack (ie empties the breadcrumb)" }
    );
    expect(browser.history.length).toBe(4);
    expect(browser.location.href).toBe("http://example.com/odoo/action-1001");

    browser.history.back();
    await animationFrame();
    expect(router.current).toEqual(
        {
            action: "menu",
            actionStack: [
                {
                    action: 1002,
                    displayName: "Client action 1002",
                },
                {
                    action: "menu",
                    displayName: "Home",
                },
            ],
            globalState: {},
        },
        { message: "actionStack was restored" }
    );
    expect(browser.history.length).toBe(4, {
        message: "the previous history entry still exists (available with forward button)",
    });
    expect(browser.location.href).toBe("http://example.com/odoo");

    await contains(".o_menu_toggle").click();
    await animationFrame();
    expect(router.current).toEqual({
        action: 1002,
        actionStack: [
            {
                action: 1002,
                displayName: "Client action 1002",
            },
        ],
    });
    expect(browser.history.length).toBe(4);
    expect(browser.location.href).toBe("http://example.com/odoo/action-1002");
});

test.tags("desktop");
test("underlying action's menu items are invisible when HomeMenu is displayed", async () => {
    defineMenus([
        {
            id: 1,
            children: [
                {
                    id: 99,
                    name: "SubMenu",
                    appID: 1,
                    actionID: 1002,
                    xmlid: "",
                    webIconData: undefined,
                    webIcon: false,
                },
            ],
        },
    ]);
    await mountWebClientEnterprise();
    expect("nav .o_menu_sections").toHaveCount(0);
    expect("nav .o_menu_brand").toHaveCount(0);
    await contains(".o_app.o_menuitem:nth-child(1)").click();
    await animationFrame();
    expect("nav .o_menu_sections").toHaveCount(1);
    expect("nav .o_menu_brand").toHaveCount(1);
    expect(".o_menu_sections").toBeVisible();
    expect(".o_menu_brand").toBeVisible();
    await contains(".o_menu_toggle").click();
    expect("nav .o_menu_sections").toHaveCount(1);
    expect("nav .o_menu_brand").toHaveCount(1);
    expect(".o_menu_sections").not.toBeVisible();
    expect(".o_menu_brand").not.toBeVisible();
});

test("go back to home menu using browser back button", async () => {
    await mountWebClientEnterprise();
    expect(".o_home_menu").toHaveCount(1);
    expect(".o_main_navbar .o_menu_toggle").not.toBeVisible();

    await contains(".o_apps > .o_draggable:nth-child(2) > .o_app").click();
    expect(".test_client_action").toHaveCount(0);
    await animationFrame();
    expect(".test_client_action").toHaveCount(1);
    expect(".o_home_menu").toHaveCount(0);

    browser.history.back();
    await animationFrame();
    await animationFrame();
    expect(".test_client_action").toHaveCount(0);
    expect(".o_home_menu").toHaveCount(1);
    expect(".o_main_navbar .o_menu_toggle").not.toBeVisible();
});

test("initial action crashes", async () => {
    expect.errors(1);
    redirect("/odoo/action-__test__client__action__?menu_id=1");
    const ClientAction = registry.category("actions").get("__test__client__action__");
    class Override extends ClientAction {
        setup() {
            super.setup();
            expect.step("clientAction setup");
            throw new Error("my error");
        }
    }
    registry.category("actions").add("__test__client__action__", Override, { force: true });

    await mountWebClientEnterprise();
    expect.verifySteps(["clientAction setup"]);
    expect("nav .o_menu_toggle").toHaveCount(1);
    expect("nav .o_menu_toggle").toBeVisible();
    expect(".o_action_manager").toHaveInnerHTML("");
    expect(router.current).toEqual({
        action: "__test__client__action__",
        menu_id: 1,
        actionStack: [
            {
                action: "__test__client__action__",
            },
        ],
    });
    await animationFrame();
    expect.verifyErrors(["my error"]);
});

test("Apps are reordered at startup based on session's user settings", async () => {
    // Config is written with apps xmlids order (default is menu_1, menu_2)
    patchWithCleanup(user, {
        get settings() {
            return { id: 1, homemenu_config: '["menu_2","menu_1"]' };
        },
    });
    await mountWebClientEnterprise();

    const apps = queryAll(".o_app");
    expect(apps[0]).toHaveAttribute("data-menu-xmlid", "menu_2", {
        message: "first displayed app has menu_2 xmlid",
    });
    expect(apps[1]).toHaveAttribute("data-menu-xmlid", "menu_1", {
        message: "second displayed app has menu_1 xmlid",
    });
    expect(apps[0]).toHaveText("App2", { message: "first displayed app is App2" });
    expect(apps[1]).toHaveText("App1", { message: "second displayed app is App1" });
});

test.tags("desktop");
test("Share URL item is present in the user menu when running as PWA", async () => {
    mockMatchMedia({ ["display-mode"]: "standalone" });
    clearRegistry(registry.category("user_menuitems"));
    // This service adds a "Dark Mode" item to the user menu items on start
    registry.category("services").remove("color_scheme");
    registry.category("user_menuitems").add("share_url", shareUrlMenuItem);

    await mountWithCleanup(UserMenu);
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item").toHaveText("Share");
});

test.tags("desktop");
test("Share URL item is not present in the user menu when not running as PWA", async () => {
    mockMatchMedia({ ["display-mode"]: "browser" });
    clearRegistry(registry.category("user_menuitems"));
    // This service adds a "Dark Mode" item to the user menu items on start
    registry.category("services").remove("color_scheme");
    registry.category("user_menuitems").add("share_url", shareUrlMenuItem);

    await mountWithCleanup(UserMenu);
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").not.toHaveCount();
});

test("Navigate to an application from the HomeMenu should generate only one pushState", async () => {
    patchWithCleanup(history, {
        pushState(state, title, url) {
            super.pushState(...arguments);
            const parsedUrl = new URL(url);
            expect.step(parsedUrl.pathname + parsedUrl.search);
        },
    });
    await mountWebClientEnterprise();

    await contains(".o_apps > .o_draggable:nth-child(2) > .o_app").click();
    await animationFrame();
    expect(".test_client_action").toHaveCount(1);
    expect(".test_client_action").toHaveText("ClientAction_Id 2");

    await goToHomeMenu();
    expect(".o_home_menu").toHaveCount(1);

    await contains(".o_apps > .o_draggable:nth-child(1) > .o_app").click();
    await animationFrame();
    expect(".test_client_action").toHaveCount(1);
    expect(".test_client_action").toHaveText("ClientAction_Id 1");

    await goToHomeMenu();
    await animationFrame();
    expect(".o_home_menu").toHaveCount(1);
    expect.verifySteps(["/odoo", "/odoo/action-1002", "/odoo", "/odoo/action-1001", "/odoo"]);
});

test.tags("desktop");
test("Should not crash when opening an app via palette and immediately entering input in the palette search", async () => {
    await mountWebClientEnterprise();

    const def = new Deferred();
    onRpc("web_search_read", () => def);
    await keyDown("a");
    await animationFrame();
    await keyDown("Enter");
    await keyDown("a");
    await animationFrame();
    def.resolve();
    await animationFrame();
    expect(".test_client_action").toHaveCount(1);
    expect(".test_client_action").toHaveText("ClientAction_Id 1");
});
