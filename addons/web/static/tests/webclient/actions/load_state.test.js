import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    getService,
    makeMockEnv,
    models,
    mountWithCleanup,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    stepAllNetworkCalls,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { router, routerBus } from "@web/core/browser/router";
import { redirect } from "@web/core/utils/urls";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { queryAllAttributes, queryAllTexts, queryFirst } from "@odoo/hoot-dom";

describe.current.tags("desktop");

const actionRegistry = registry.category("actions");

function logHistoryInteractions() {
    patchWithCleanup(browser.history, {
        pushState(state, _, url) {
            expect.step(`pushState ${url}`);
            return super.pushState(state, _, url);
        },
        replaceState(state, _, url) {
            if (browser.location.href === url) {
                expect.step(
                    `Update the state without updating URL, nextState: ${Object.keys(
                        state?.nextState
                    )}`
                );
            } else {
                expect.step(`replaceState ${url}`);
            }
            return super.pushState(state, _, url);
        },
    });
}

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
        type: "ir.actions.server",
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
    {
        id: 1099,
        xml_id: "wowl.client_action",
        tag: "__test__client__action__",
        target: "main",
        type: "ir.actions.client",
        params: { description: "xmlId" },
    },
]);

defineMenus([
    { id: 0 }, // prevents auto-loading the first action
    { id: 1, actionID: 1001 },
    { id: 2, actionID: 1002 },
]);

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });
    child_ids = fields.One2many({ relation: "partner", relation_field: "parent_id" });

    _records = [
        { id: 1, name: "First record", foo: "yop" },
        { id: 2, name: "Second record", foo: "blip" },
        { id: 3, name: "Third record", foo: "gnap" },
        { id: 4, name: "Fourth record", foo: "plop" },
        { id: 5, name: "Fifth record", foo: "zoup" },
    ];
    _views = {
        "kanban,1": /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        "list,2": /* xml */ `
            <list>
                <field name="foo" />
            </list>
        `,
        "form,666": /* xml */ `
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
        search: /* xml */ `
            <search>
                <field name="foo" string="Foo" />
            </search>
        `,
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
    patchWithCleanup(browser.location, {
        origin: "http://example.com",
    });
    redirect("/odoo");
});

describe(`new urls`, () => {
    test(`action loading`, async () => {
        redirect("/odoo/action-1001");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.test_client_action`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveText("App1");
        expect(browser.sessionStorage.getItem("menu_id")).toBe("1");
        expect(browser.location.href).toBe("http://example.com/odoo/action-1001", {
            message: "url did not change",
        });
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

    test(`menu loading`, async () => {
        redirect("/odoo?menu_id=2");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_Id 2");
        expect(`.o_menu_brand`).toHaveText("App2");
        expect(browser.sessionStorage.getItem("menu_id")).toBe("2");
        expect(browser.location.href).toBe("http://example.com/odoo/action-1002", {
            message: "url now points to the default action of the menu",
        });
        expect.verifySteps(["pushState http://example.com/odoo/action-1002"]);
    });

    test(`action and menu loading`, async () => {
        redirect("/odoo/action-1001?menu_id=2");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_Id 1");
        expect(`.o_menu_brand`).toHaveText("App2");
        expect(browser.sessionStorage.getItem("menu_id")).toBe("2");
        expect(router.current).toEqual({
            action: 1001,
            actionStack: [
                {
                    action: 1001,
                    displayName: "Client action 1001",
                },
            ],
        });
        expect(browser.location.href).toBe("http://example.com/odoo/action-1001", {
            message: "menu is removed from url",
        });
        expect.verifySteps(["pushState http://example.com/odoo/action-1001"]);
    });

    test("menu fallback", async () => {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static path = "test";
            static props = ["*"];
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        browser.sessionStorage.setItem("menu_id", 2);
        redirect("/odoo/test");
        logHistoryInteractions();
        await mountWebClient();

        expect(`.o_menu_brand`).toHaveText("App2");
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

    test(`initial loading with action id`, async () => {
        redirect("/odoo/action-1001");
        logHistoryInteractions();
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWithCleanup(WebClient, { env });
        expect(browser.location.href).toBe("http://example.com/odoo/action-1001", {
            message: "url did not change",
        });

        await animationFrame();
        expect.verifySteps(["/web/action/load"]);
    });

    test(`initial loading take complete context`, async () => {
        redirect("/odoo/action-1001");
        logHistoryInteractions();

        onRpc("/web/action/load", async (route) => {
            const { params } = await route.json();
            expect.step(params.context);
        });
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWithCleanup(WebClient, { env });
        user.updateContext({ an_extra_context: 22 });
        expect(browser.location.href).toBe("http://example.com/odoo/action-1001", {
            message: "url did not change",
        });

        await animationFrame();
        expect.verifySteps([
            "/web/action/load",
            { lang: "en", tz: "taht", uid: 7, allowed_company_ids: [1], an_extra_context: 22 },
        ]);
    });

    test(`initial loading with action tag`, async () => {
        redirect("/odoo/__test__client__action__");
        logHistoryInteractions();
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWithCleanup(WebClient, { env });
        expect(browser.location.href).toBe("http://example.com/odoo/__test__client__action__", {
            message: "url did not change",
        });
        expect.verifySteps([]);
    });

    test(`fallback on home action if no action found`, async () => {
        logHistoryInteractions();
        patchWithCleanup(user, { homeActionId: 1001 });
        expect(browser.location.href).toBe("http://example.com/odoo");

        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/action-1001");
        expect.verifySteps(["pushState http://example.com/odoo/action-1001"]);
        expect(`.test_client_action`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveText("App1");
    });

    test(`correctly sends additional context`, async () => {
        // %2C is a URL-encoded comma
        redirect("/odoo/4/action-1001");
        logHistoryInteractions();
        onRpc("/web/action/load", async (request) => {
            expect.step("/web/action/load");
            const { params } = await request.json();
            expect(params).toEqual({
                action_id: 1001,
                context: {
                    active_id: 4, // aditional context
                    active_ids: [4], // aditional context
                    lang: "en", // user context
                    tz: "taht", // user context
                    uid: 7, // user context
                    allowed_company_ids: [1],
                },
            });
        });

        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/4/action-1001", {
            message: "url did not change",
        });
        expect.verifySteps([
            "/web/action/load",
            "Update the state without updating URL, nextState: actionStack,action,active_id",
        ]);
    });

    test(`supports action as xmlId`, async () => {
        redirect("/odoo/action-wowl.client_action");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_xmlId");
        expect(`.o_menu_brand`).toHaveCount(0);
        expect(browser.location.href).toBe(
            // FIXME should we canonicalize the URL? If yes, shouldn't we use the client action tag instead? {
            "http://example.com/odoo/action-1099",
            { message: "url did not change" }
        );
        expect.verifySteps(["pushState http://example.com/odoo/action-1099"]);
    });

    test(`supports opening action in dialog`, async () => {
        defineActions(
            [
                {
                    id: 1099,
                    xml_id: "wowl.client_action",
                    tag: "__test__client__action__",
                    target: "new",
                    type: "ir.actions.client",
                    params: { description: "xmlId" },
                },
            ],
            { mode: "replace" }
        );
        // FIXME this is super weird: we open an action in target new from the url?
        redirect("/odoo/action-wowl.client_action");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.test_client_action`).toHaveCount(1);
        expect(`.modal .test_client_action`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveCount(0);
        expect(browser.location.href).toBe("http://example.com/odoo/action-wowl.client_action", {
            message: "action in target new doesn't affect the URL",
        });
        expect.verifySteps([]);
    });

    test(`should not crash on invalid state`, async () => {
        redirect("/odoo/m-partner?view_type=list");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_action_manager`).toHaveText("", { message: "should display nothing" });
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
        expect(browser.location.href).toBe("http://example.com/odoo/m-partner?view_type=list", {
            message: "the url did not change",
        });
        // No default action was found, no action controller was mounted: pushState not called
        expect.verifySteps([]);
    });

    test(`properly load client actions`, async () => {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/HelloWorldTest", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

    test(`properly load client actions with path`, async () => {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static path = "my-action";
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(router.current).toEqual({
            action: "my-action",
            actionStack: [
                {
                    action: "my-action",
                    displayName: "",
                },
            ],
        });
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/my-action");
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "pushState http://example.com/odoo/my-action",
        ]);
    });

    test(`properly load client actions with resId`, async () => {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };

            setup() {
                expect.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/HelloWorldTest/12");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/HelloWorldTest/12", {
            message: "the url did not change",
        });
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Client Action DisplayName",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "resId:12",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);
    });

    test(`properly load client actions with updateActionState`, async () => {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };

            setup() {
                onMounted(() => {
                    this.props.updateActionState({ resId: 12 });
                });
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/HelloWorldTest/12", {
            message: "the url did change (the resId was added)",
        });
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Client Action DisplayName",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "pushState http://example.com/odoo/HelloWorldTest/12",
        ]);
    });

    test(`properly load client actions with resId and path (1)`, async () => {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };
            static path = "my_client";

            setup() {
                expect.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/HelloWorldTest/12");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/my_client/12");
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Client Action DisplayName",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "resId:12",
            "pushState http://example.com/odoo/my_client/12",
        ]);
    });

    test(`properly load client actions with resId and path (2)`, async () => {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };
            static path = "my_client";

            setup() {
                expect.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/my_client/12");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/my_client/12");
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Client Action DisplayName",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "resId:12",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);
    });

    test(`properly load client actions with LazyTranslatedString displayName`, async () => {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = _t("translatable displayname");
            static components = { ControlPanel };
            static path = "my_client";
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/odoo/my_client");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect(browser.location.href).toBe("http://example.com/odoo/my_client");
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "translatable displayname",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

    test(`properly load act window actions`, async () => {
        redirect("/odoo/action-1");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_control_panel`).toHaveCount(1);
        expect(`.o_kanban_view`).toHaveCount(1);
        expect(browser.location.href).toBe("http://example.com/odoo/action-1", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

    test(`properly load records`, async () => {
        redirect("/odoo/m-partner/2");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(browser.location.href).toBe("http://example.com/odoo/m-partner/2", {
            message: "the url did not change",
        });
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Second record"]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_read",
            "Update the state without updating URL, nextState: actionStack,resId,model",
        ]);
    });

    test(`properly load records with existing first APP`, async () => {
        // simulate a real scenario with a first app (e.g. Discuss), to ensure that we don't
        // fallback on that first app when only a model and res_id are given in the url
        redirect("/odoo/m-partner/2");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveCount(0);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Second record"]);
        expect(browser.location.href).toBe("http://example.com/odoo/m-partner/2", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_read",
            "Update the state without updating URL, nextState: actionStack,resId,model",
        ]);
    });

    test(`properly load default record`, async () => {
        redirect("/odoo/action-3/new");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/new", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);
    });

    test(`load requested view for act window actions`, async () => {
        redirect("/odoo/action-3?view_type=kanban");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(0);
        expect(`.o_kanban_view`).toHaveCount(1);
        expect(browser.location.href).toBe("http://example.com/odoo/action-3?view_type=kanban", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "Update the state without updating URL, nextState: actionStack,action,view_type",
        ]);
    });

    test(`lazy load multi record view if mono record one is requested`, async () => {
        redirect("/odoo/action-3/2");
        logHistoryInteractions();

        onRpc("unity_read", ({ kwargs }) => expect.step(`unity_read ${kwargs.method}`));
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(0);
        expect(`.o_form_view`).toHaveCount(1);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners",
            "Second record",
        ]);
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/2", {
            message: "the url did not change",
        });
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_read",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);

        // go back to List
        await contains(`.o_control_panel .breadcrumb a`).click();
        expect(`.o_list_view`).toHaveCount(1);
        expect(`.o_form_view`).toHaveCount(0);
        expect.verifySteps(["web_search_read", "has_group"]);

        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-3");
        expect.verifySteps(["pushState http://example.com/odoo/action-3"]);
    });

    test(`go back with breadcrumbs after doAction`, async () => {
        logHistoryInteractions();

        await mountWebClient();
        await getService("action").doAction(4);
        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-4");
        expect.verifySteps(["pushState http://example.com/odoo/action-4"]);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners Action 4",
        ]);

        await getService("action").doAction(3, {
            props: { resId: 2 },
            viewType: "form",
        });
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners Action 4",
            "Second record",
        ]);

        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-4/action-3/2");
        // pushState was called only once
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action,globalState",
            "pushState http://example.com/odoo/action-4/action-3/2",
        ]);

        // go back to previous action
        await contains(`.o_control_panel .breadcrumb .o_back_button a`).click();
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners Action 4",
        ]);

        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-4");
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,resId,action,globalState",
            "pushState http://example.com/odoo/action-4",
        ]);
    });

    test(`lazy loaded multi record view with failing mono record one`, async () => {
        expect.errors(1);

        redirect("/odoo/action-3/2");
        logHistoryInteractions();
        onRpc("web_read", () => Promise.reject());

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(0);
        expect(`.o_list_view`).toHaveCount(1); // Show the lazy loaded list view
        expect(browser.location.href).toBe("http://example.com/odoo/action-3", {
            message: "url reflects that we are not on the failing record",
        });
        expect.verifySteps(["pushState http://example.com/odoo/action-3"]);

        await getService("action").doAction(1);
        expect(`.o_kanban_view`).toHaveCount(1);

        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/action-1");
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action,globalState",
            "pushState http://example.com/odoo/action-3/action-1",
        ]);
        expect.verifyErrors([/RPC_ERROR/]);
    });

    test(`should push the correct state at the right time`, async () => {
        // formerly "should not push a loaded state"
        redirect("/odoo/action-3");
        logHistoryInteractions();

        await mountWebClient();
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
        expect(browser.location.href).toBe("http://example.com/odoo/action-3");
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action",
        ]);

        await contains(`tr .o_data_cell`).click();
        await animationFrame(); // pushState is debounced
        expect(router.current).toEqual({
            action: 3,
            resId: 1,
            actionStack: [
                {
                    action: 3,
                    displayName: "Partners",
                    view_type: "list",
                },
                {
                    action: 3,
                    resId: 1,
                    displayName: "First record",
                    view_type: "form",
                },
            ],
        });
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/1");
        // should push the state if it changes afterwards
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,action,globalState",
            "pushState http://example.com/odoo/action-3/1",
        ]);
    });

    test(`load state supports being given menu_id alone`, async () => {
        defineMenus([{ id: 666, actionID: 1 }]);

        redirect("/odoo?menu_id=666");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_kanban_view`).toHaveCount(1, { message: "should display a kanban view" });
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners Action 1",
        ]);
        expect(browser.location.href).toBe("http://example.com/odoo/action-1");
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "pushState http://example.com/odoo/action-1",
        ]);
    });

    test(`load state: in a form view, no id in initial state`, async () => {
        defineActions([
            {
                id: 999,
                name: "Partner",
                res_model: "partner",
                views: [
                    [false, "list"],
                    [666, "form"],
                ],
            },
        ]);

        redirect("/odoo/action-999/new");
        logHistoryInteractions();
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Partner", "New"]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);
        expect(`.o_form_view .o_form_editable`).toHaveCount(1);
        expect(browser.location.href).toBe("http://example.com/odoo/action-999/new");
    });

    test(`load state: in a form view, wrong id in the state`, async () => {
        expect.errors(1);

        defineActions([
            {
                id: 1000,
                name: "Partner",
                res_model: "partner",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        ]);

        redirect("/odoo/action-1000/999");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(1);
        expect(`.o_notification_body`).toHaveCount(1, { message: "should have a notification" });
        expect(browser.location.href).toBe("http://example.com/odoo/action-1000", {
            message: "url reflects that we are not on the record",
        });
        expect.verifySteps(["pushState http://example.com/odoo/action-1000"]);
        expect.verifyErrors([
            /It seems the records with IDs 999 cannot be found. They might have been deleted./,
        ]);
    });

    test(`server action loading with id`, async () => {
        redirect("/odoo/action-2/2");
        logHistoryInteractions();

        onRpc("/web/action/run", async (request) => {
            const { params } = await request.json();
            expect.step(`action: ${params.action_id}`);
            return new Promise(() => {});
        });

        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/action-2/2", {
            message: "url did not change",
        });
        expect.verifySteps(["action: 2"]);
    });

    test("server action returning act_window", async () => {
        defineActions([
            {
                id: 2000,
                xml_id: "action_2000",
                type: "ir.actions.server",
                path: "my-path",
            },
        ]);
        onRpc("/web/action/run", async (request) => {
            const { params } = await request.json();
            expect.step(`action: ${params.action_id}`);
            return {
                name: "Partners",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            };
        });
        redirect("/odoo/my-path/2");
        logHistoryInteractions();
        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/my-path/2", {
            message: "url did not change",
        });
        expect(router.current).toEqual({
            action: "my-path",
            actionStack: [
                {
                    action: "my-path",
                    displayName: "Partners",
                    view_type: "list",
                },
                {
                    action: "my-path",
                    displayName: "Second record",
                    resId: 2,
                    view_type: "form",
                },
            ],
            resId: 2,
        });
        expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
            "Partners",
            "Second record",
        ]);
        expect.verifySteps([
            "action: 2000",
            "Update the state without updating URL, nextState: actionStack,resId,action", // "pushState was not called"
        ]);
    });

    test(`state with integer active_ids should not crash`, async () => {
        redirect("/odoo/action-2?active_ids=3");
        logHistoryInteractions();

        onRpc("/web/action/run", async (request) => {
            const { params } = await request.json();
            const { action_id, context } = params;
            expect.step({ action: action_id, active_ids: context.active_ids });
            return new Promise(() => {});
        });

        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/action-2?active_ids=3", {
            message: "url did not change",
        });
        // pushState was not called
        expect.verifySteps([{ action: 2, active_ids: [3] }]);
    });

    test(`load a form view via url, then switch to view list, the search view is correctly initialized`, async () => {
        Partner._views.search = `
                <search>
                    <filter name="filter" string="Filter" domain="[('foo', '=', 'yop')]"/>
                </search>
            `;

        redirect("/odoo/action-3/new");
        logHistoryInteractions();

        await mountWebClient();
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/new", {
            message: "url did not change",
        });
        expect.verifySteps([
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);

        await contains(`.o_control_panel .breadcrumb-item`).click();
        expect(`.o_list_view .o_data_row`).toHaveCount(5);

        await toggleSearchBarMenu();
        await toggleMenuItem("Filter");
        expect(`.o_list_view .o_data_row`).toHaveCount(1);

        await animationFrame(); // pushState is debounced
        expect(browser.location.href).toBe("http://example.com/odoo/action-3");
        expect.verifySteps(["pushState http://example.com/odoo/action-3"]);
    });

    test(`initial action crashes`, async () => {
        expect.errors(1);

        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                expect.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        redirect("/odoo/__test__client__action__?menu_id=1");
        logHistoryInteractions();

        await mountWebClient();
        expect.verifySteps(["clientAction setup"]);
        expect(browser.location.href).toBe(
            "http://example.com/odoo/__test__client__action__?menu_id=1",
            {
                message: "url did not change",
            }
        );

        await animationFrame();
        expect.verifyErrors(["my error"]);
        expect(`.o_error_dialog`).toHaveCount(1);

        await contains(`.modal-header .btn-close`).click();
        expect(`.o_error_dialog`).toHaveCount(0);

        await contains(`nav .o_navbar_apps_menu .dropdown-toggle`).click();
        expect(`.dropdown-item.o_app`).toHaveCount(3);
        expect(`.o_action_manager`).toHaveText("");

        await animationFrame(); // pushState is debounced
        expect(router.current).toEqual({
            action: "__test__client__action__",
            menu_id: 1,
            actionStack: [
                {
                    action: "__test__client__action__",
                },
            ],
        });
        expect(browser.location.href).toBe(
            "http://example.com/odoo/__test__client__action__?menu_id=1",
            {
                message: "url did not change",
            }
        );
        // pushState was not called
        expect.verifySteps([]);
    });

    test("all actions crashes", async () => {
        expect.errors(2);
        redirect("/odoo/m-partner/2/m-partner/1");
        logHistoryInteractions();
        stepAllNetworkCalls();
        onRpc("web_read", () => Promise.reject());

        await mountWebClient();
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load_breadcrumbs",
            "get_views",
            "web_read",
            "web_read",
        ]);
        expect.verifyErrors([/RPC_ERROR/, /RPC_ERROR/]);
        expect(queryFirst(`.o_action_manager`).childElementCount).toBe(0);
    });

    test(`initial loading with multiple path segments loads the breadcrumbs`, async () => {
        defineActions(
            [
                {
                    id: 27,
                    xml_id: "action_27",
                    name: "Partners Action 27",
                    res_model: "partner",
                    path: "partners",
                    views: [
                        [false, "list"],
                        [1, "kanban"],
                        [false, "form"],
                    ],
                },
                {
                    id: 28,
                    xml_id: "action_28",
                    name: "Partners Action 28",
                    res_model: "partner",
                    views: [
                        [1, "kanban"],
                        [2, "list"],
                        [false, "form"],
                    ],
                },
            ],
            { mode: "replace" }
        );

        redirect("/odoo/partners/2/action-28/1");
        logHistoryInteractions();
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWithCleanup(WebClient, { env });
        await animationFrame();
        await animationFrame();

        expect(browser.location.href).toBe("http://example.com/odoo/partners/2/action-28/1", {
            message: "url did not change",
        });
        expect.verifySteps([
            "/web/action/load_breadcrumbs",
            "/web/action/load",
            "get_views",
            "web_read",
            "Update the state without updating URL, nextState: actionStack,resId,action,active_id",
        ]);

        await contains(`.breadcrumb .dropdown-toggle`).click();
        expect(`.o-overlay-container .dropdown-menu`).toHaveText("Partners Action 27");
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "",
            "Second record",
            "Partners Action 28",
            "First record",
        ]);
        expect(`.o-overlay-container .dropdown-menu a`).toHaveAttribute(
            "data-tooltip",
            "Back to “Partners Action 27”"
        );
        expect(queryAllAttributes(".o_breadcrumb li.breadcrumb-item a", "data-tooltip")).toEqual([
            'Back to "Second record" form',
            'Back to "Partners Action 28"',
        ]);
    });

    test(`don't load controllers when load action new`, async () => {
        stepAllNetworkCalls();
        redirect("/odoo/action-3/2");
        logHistoryInteractions();
        Partner._views["form"] = /* xml */ `
            <form string="Partner">
                <sheet>
                    <a href="http://example.com/odoo/action-5" class="clickMe">clickMe</a>
                    <group>
                        <field name="display_name"/>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `;
        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
            "Partners",
            "Second record",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_read",
            "Update the state without updating URL, nextState: actionStack,resId,action",
        ]);
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/2", {
            message: "url did not change",
        });

        // Open the dialog
        await contains(`.clickMe`).click();
        await animationFrame();
        expect(`.o_dialog .o_form_view`).toHaveCount(1);
        expect.verifySteps(["/web/action/load", "get_views", "onchange"]);
        expect(browser.location.href).toBe("http://example.com/odoo/action-3/2", {
            message: "url did not change",
        });

        // Close te dialog
        await contains(`.o_dialog .o_form_button_cancel`).click();

        // Go back to the multi-record view
        await contains(`.breadcrumb-item`).click();
        await animationFrame();
        expect(`.o_list_view`).toHaveCount(1);
        expect.verifySteps([
            "web_search_read",
            "has_group",
            "pushState http://example.com/odoo/action-3",
        ]);
    });

    test("properly load previous action when error", async () => {
        // In this test, the _getActionParams, will not return m-partner as an actionRequest
        // because, there is not id, or an action on the session storage.
        // So it will try to perform the previous action : action-3 with id 1.
        // This one will give an error, and it should directly try the previous one : action-3
        expect.errors(1);
        redirect("/odoo/action-3/1/m-partner");
        logHistoryInteractions();
        stepAllNetworkCalls();
        onRpc("web_read", () => Promise.reject());

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(1);
        expect.verifyErrors([/RPC_ERROR/]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load_breadcrumbs",
            "/web/action/load",
            "get_views",
            "web_read",
            "web_search_read",
            "has_group",
            "pushState http://example.com/odoo/action-3",
        ]);
    });

    test("properly reload dynamic actions from sessionStorage", async () => {
        patchWithCleanup(browser.sessionStorage, {
            setItem(key, value) {
                expect.step(`set ${key}-${value}`);
                super.setItem(key, value);
            },
            getItem(key) {
                const res = super.getItem(key);
                expect.step(`get ${key}-${res}`);
                return res;
            },
        });

        onRpc("/web/dataset/call_button/partner/object", () => ({
            type: "ir.actions.act_window",
            res_model: "partner",
            views: [[1, "kanban"]],
        }));
        await mountWebClient();

        await getService("action").doAction({
            type: "ir.actions.act_window",
            res_model: "partner",
            res_id: 1,
            views: [[false, "form"]],
        });

        expect(`.o_form_view`).toHaveCount(1);

        await contains(`.o_statusbar_buttons .btn-secondary[type='object']`).click();
        await animationFrame();

        expect(`.o_kanban_view`).toHaveCount(1);
        expect.verifySteps([
            "get menu_id-null",
            'set current_action-{"type":"ir.actions.act_window","res_model":"partner","res_id":1,"views":[[false,"form"]]}',
            'set current_action-{"type":"ir.actions.act_window","res_model":"partner","views":[[1,"kanban"]],"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_model":"partner","active_id":1,"active_ids":[1]}}',
        ]);

        expect(browser.location.href).toBe("http://example.com/odoo/m-partner/1/m-partner");

        // Emulate a Reload
        routerBus.trigger("ROUTE_CHANGE");
        await animationFrame();
        await animationFrame();
        expect(`.o_kanban_view`).toHaveCount(1);
        expect.verifySteps([
            "get menu_id-null",
            'get current_action-{"type":"ir.actions.act_window","res_model":"partner","views":[[1,"kanban"]],"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_model":"partner","active_id":1,"active_ids":[1]}}',
            'set current_action-{"type":"ir.actions.act_window","res_model":"partner","views":[[1,"kanban"]],"context":{"lang":"en","tz":"taht","uid":7,"active_model":"partner","active_id":1,"active_ids":[1]}}',
        ]);
    });

    test("menu jumping fix: multiple menus sharing same action", async () => {
        // Test case for menu jumping issue when multiple menus share the same action
        // Scenario: User navigates to Sale->Customers, then F5 reload should stay in Sale, not jump to Account
        defineActions([
            {
                id: 9001,
                name: "Partners",
                res_model: "partner", 
                type: "ir.actions.act_window",
                views: [[false, "list"], [false, "form"]],
            },
        ]);

        defineMenus([
            { id: 0 }, // prevents auto-loading
            // Sale App
            { id: 100, name: "Sale", appID: 100, children: [101] },
            { id: 101, name: "Customers", appID: 100, actionID: 9001, parent_id: 100 },
            // Account App  
            { id: 200, name: "Accounting", appID: 200, children: [201] },
            { id: 201, name: "Customers", appID: 200, actionID: 9001, parent_id: 200 }, // Same action!
        ]);

        patchWithCleanup(browser.sessionStorage, {
            setItem(key, value) {
                expect.step(`set ${key}-${value}`);
                super.setItem(key, value);
            },
            getItem(key) {
                const res = super.getItem(key);
                expect.step(`get ${key}-${res}`);
                return res;
            },
        });

        // Step 1: Navigate to Sale->Customers with explicit menu_id
        redirect("/odoo/action-9001?menu_id=100");
        logHistoryInteractions();

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(1);

        // Step 2: Emulate F5 reload
        routerBus.trigger("ROUTE_CHANGE");
        await animationFrame();
        await animationFrame();

        expect(`.o_list_view`).toHaveCount(1);

        expect.verifySteps([
            "get menu_id-null",
            "set menu_id-100",
            'set current_action-{"binding_type":"action","binding_view_types":"list,form","id":9001,"type":"ir.actions.act_window","xml_id":9001,"name":"Partners","res_model":"partner","views":[[false,"list"],[false,"form"]],"context":{},"embedded_action_ids":[],"group_ids":[],"limit":80,"mobile_view_mode":"kanban","target":"current","view_ids":[],"view_mode":"list,form"}',
            "pushState http://example.com/odoo/action-9001",
            "get menu_id-100", // F5 reload checks stored menu
            'set current_action-{"binding_type":"action","binding_view_types":"list,form","id":9001,"type":"ir.actions.act_window","xml_id":9001,"name":"Partners","res_model":"partner","views":[[false,"list"],[false,"form"]],"context":{},"embedded_action_ids":[],"group_ids":[],"limit":80,"mobile_view_mode":"kanban","target":"current","view_ids":[],"view_mode":"list,form"}',
            "Update the state without updating URL, nextState: actionStack,action",
        ]);
    });

});

describe(`legacy urls`, () => {
    test(`action loading`, async () => {
        redirect("/web#action=1001");

        await mountWebClient();
        expect(`.test_client_action`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveText("App1");
    });

    test(`menu loading`, async () => {
        redirect("/web#menu_id=2");

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_Id 2");
        expect(`.o_menu_brand`).toHaveText("App2");
    });

    test(`action and menu loading`, async () => {
        redirect("/web#action=1001&menu_id=2");

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_Id 1");
        expect(`.o_menu_brand`).toHaveText("App2");
        expect(router.current).toEqual({
            action: 1001,
            actionStack: [
                {
                    action: 1001,
                    displayName: "Client action 1001",
                },
            ],
        });
    });

    test(`initial loading with action id`, async () => {
        redirect("/web#action=1001");
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWebClient({ env });
        expect.verifySteps(["/web/action/load"]);
    });

    test(`initial loading with action tag`, async () => {
        redirect("/web#action=__test__client__action__");
        stepAllNetworkCalls();

        const env = await makeMockEnv();
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

        await mountWebClient({ env });
        expect.verifySteps([]);
    });

    test(`correctly sends additional context`, async () => {
        redirect("/web#action=1001&active_id=4&active_ids=4,8");
        onRpc("/web/action/load", async (request) => {
            expect.step("/web/action/load");
            const { params } = await request.json();
            expect(params).toEqual({
                action_id: 1001,
                context: {
                    active_id: 4, // aditional context
                    active_ids: [4, 8], // aditional context
                    lang: "en", // user context
                    tz: "taht", // user context
                    uid: 7, // user context
                    allowed_company_ids: [1],
                },
            });
        });

        await mountWebClient();
        expect.verifySteps(["/web/action/load"]);
    });

    test(`supports action as xmlId`, async () => {
        redirect("/web#action=wowl.client_action");

        await mountWebClient();
        expect(`.test_client_action`).toHaveText("ClientAction_xmlId");
        expect(`.o_menu_brand`).toHaveCount(0);
    });

    test(`supports opening action in dialog`, async () => {
        defineActions(
            [
                {
                    id: 1099,
                    xml_id: "wowl.client_action",
                    tag: "__test__client__action__",
                    target: "new",
                    type: "ir.actions.client",
                    params: { description: "xmlId" },
                },
            ],
            { mode: "replace" }
        );
        redirect("/web#action=wowl.client_action");

        await mountWebClient();
        expect(`.test_client_action`).toHaveCount(1);
        expect(`.modal .test_client_action`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveCount(0);
    });

    test(`should not crash on invalid state`, async () => {
        redirect("/web#res_model=partner");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_action_manager`).toHaveText("", { message: "should display nothing" });
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
    });

    test(`properly load client actions`, async () => {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
        }
        actionRegistry.add("HelloWorldTest", ClientAction);

        redirect("/web#action=HelloWorldTest");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_client_action_test`).toHaveText("Hello World", {
            message: "should have correctly rendered the client action",
        });
        expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);
    });

    test(`properly load act window actions`, async () => {
        redirect("/web#action=1");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_control_panel`).toHaveCount(1);
        expect(`.o_kanban_view`).toHaveCount(1);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    test(`properly load records`, async () => {
        redirect("/web#id=2&model=partner");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Second record"]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_read",
        ]);
    });

    test(`properly load records with existing first APP`, async () => {
        // simulate a real scenario with a first app (e.g. Discuss), to ensure that we don't
        // fallback on that first app when only a model and res_id are given in the url
        redirect("/web#id=2&model=partner");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(`.o_menu_brand`).toHaveCount(0);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Second record"]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_read",
        ]);
    });

    test(`properly load default record`, async () => {
        redirect("/web#action=3&id=&model=partner&view_type=form");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]);
    });

    test(`load requested view for act window actions`, async () => {
        redirect("/web#action=3&view_type=kanban");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(0);
        expect(`.o_kanban_view`).toHaveCount(1);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    test(`lazy load multi record view if mono record one is requested`, async () => {
        redirect("/web#action=3&id=2&view_type=form");
        stepAllNetworkCalls();
        onRpc("unity_read", ({ kwargs }) => {
            expect.step(`unity_read ${kwargs.method}`);
        });

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(0);
        expect(`.o_form_view`).toHaveCount(1);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners",
            "Second record",
        ]);

        // go back to List
        await contains(`.o_control_panel .breadcrumb a`).click();
        expect(`.o_list_view`).toHaveCount(1);
        expect(`.o_form_view`).toHaveCount(0);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_read",
            "web_search_read",
            "has_group",
        ]);
    });

    test(`lazy loaded multi record view with failing mono record one`, async () => {
        expect.errors(1);

        redirect("/web#action=3&id=2&view_type=form");
        onRpc("web_read", () => Promise.reject());

        await mountWebClient();

        expect.verifyErrors([Error]);
        expect(`.o_form_view`).toHaveCount(0);
        expect(`.o_list_view`).toHaveCount(1); // Show the lazy loaded list view

        await getService("action").doAction(1);
        expect(`.o_kanban_view`).toHaveCount(1);
    });

    test(`should push the correct state at the right time`, async () => {
        redirect("/web#action=3");
        patchWithCleanup(browser.history, {
            pushState(...args) {
                expect.step(`pushState`);
                return super.pushState(...args);
            },
        });

        await mountWebClient();
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
        // loading the initial state shouldn't push the state
        expect.verifySteps([]);

        await contains(`tr .o_data_cell`).click();
        await animationFrame();
        expect(router.current).toEqual({
            action: 3,
            resId: 1,
            actionStack: [
                {
                    action: 3,
                    displayName: "Partners",
                    view_type: "list",
                },
                {
                    action: 3,
                    resId: 1,
                    displayName: "First record",
                    view_type: "form",
                },
            ],
        });
        // should push the state of it changes afterwards
        expect.verifySteps(["pushState"]);
    });

    test(`load state supports being given menu_id alone`, async () => {
        defineMenus([
            {
                id: 666,
                name: "App1",
                actionID: 1,
            },
        ]);

        redirect("/web#menu_id=666");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_kanban_view`).toHaveCount(1, { message: "should display a kanban view" });
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual([
            "Partners Action 1",
        ]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    test(`load state: in a form view, no id in initial state`, async () => {
        defineActions(
            [
                {
                    id: 999,
                    name: "Partner",
                    res_model: "partner",
                    views: [
                        [false, "list"],
                        [666, "form"],
                    ],
                },
            ],
            { mode: "replace" }
        );

        redirect("/web#action=999&view_type=form&id=");
        stepAllNetworkCalls();

        await mountWebClient();
        expect(`.o_form_view`).toHaveCount(1);
        expect(`.o_form_view .o_form_editable`).toHaveCount(1);
        expect(queryAllTexts`.breadcrumb-item, .o_breadcrumb .active`).toEqual(["Partner", "New"]);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]);
    });

    test(`load state: in a form view, wrong id in the state`, async () => {
        expect.errors(1);

        defineActions(
            [
                {
                    id: 1000,
                    name: "Partner",
                    res_model: "partner",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                },
            ],
            { mode: "replace" }
        );

        redirect("/web#action=1000&view_type=form&id=999");

        await mountWebClient();
        expect(`.o_list_view`).toHaveCount(1);
        expect(`.o_notification_body`).toHaveCount(1, { message: "should have a notification" });
        expect.verifyErrors([
            /It seems the records with IDs 999 cannot be found. They might have been deleted./,
        ]);
    });

    test(`state with integer active_ids should not crash`, async () => {
        redirect("/web#action=2&active_ids=3");
        onRpc("/web/action/run", async (request) => {
            const { params } = await request.json();
            const { action_id, context } = params;
            expect.step({ action: action_id, active_ids: context.active_ids });
            return new Promise(() => {});
        });

        await mountWebClient();
        // pushState was not called
        expect.verifySteps([{ action: 2, active_ids: [3] }]);
    });

    test(`charge a form view via url, then switch to view list, the search view is correctly initialized`, async () => {
        Partner._views.search = `
                <search>
                    <filter name="filter" string="Filter" domain="[('foo', '=', 'yop')]"/>
                </search>
            `;

        redirect("/web#action=3&model=partner&view_type=form");

        await mountWebClient();
        await contains(`.o_control_panel .breadcrumb-item`).click();
        expect(`.o_list_view .o_data_row`).toHaveCount(5);

        await toggleSearchBarMenu();
        await toggleMenuItem("Filter");
        expect(`.o_list_view .o_data_row`).toHaveCount(1);
    });

    test(`initial action crashes`, async () => {
        expect.errors(1);

        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                expect.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        redirect("/web#action=__test__client__action__&menu_id=1");

        await mountWebClient();
        expect.verifySteps(["clientAction setup"]);

        await animationFrame();
        expect.verifyErrors(["my error"]);
        expect(`.o_error_dialog`).toHaveCount(1);

        await contains(`.modal-header .btn-close`).click();
        expect(`.o_error_dialog`).toHaveCount(0);

        await contains(`nav .o_navbar_apps_menu .dropdown-toggle`).click();
        expect(`.dropdown-item.o_app`).toHaveCount(3);
        expect(`.o_menu_brand`).toHaveText("App1");
        expect(`.o_action_manager`).toHaveText("");
        expect(router.current).toEqual({
            action: "__test__client__action__",
            menu_id: 1,
            actionStack: [
                {
                    action: "__test__client__action__",
                },
            ],
        });
    });
});
