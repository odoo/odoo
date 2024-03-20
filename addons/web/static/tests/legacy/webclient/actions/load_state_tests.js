/** @odoo-module alias=@web/../tests/webclient/actions/load_state_tests default=false */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { makeTestEnv } from "../../helpers/mock_env";
import { patchUserWithCleanup } from "../../helpers/mock_services";
import {
    click,
    getFixture,
    patchWithCleanup,
    mount,
    nextTick,
    getNodesTextContent,
} from "../../helpers/utils";
import { toggleMenuItem, toggleSearchBarMenu } from "@web/../tests/search/helpers";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
    setupWebClientRegistries,
} from "./../helpers";
import { errorService } from "@web/core/errors/error_service";
import { router, startRouter } from "@web/core/browser/router";

import { Component, onMounted, xml } from "@odoo/owl";
import { redirect } from "@web/core/utils/urls";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { _t } from "@web/core/l10n/translation";

function getBreadCrumbTexts(target) {
    return getNodesTextContent(target.querySelectorAll(".breadcrumb-item, .o_breadcrumb .active"));
}

let serverData;
let target;

const actionRegistry = registry.category("actions");

const logHistoryInteractions = (assert) => {
    patchWithCleanup(browser.history, {
        pushState(state, _, url) {
            assert.step(`pushState ${url}`);
            return super.pushState(state, _, url);
        },
        replaceState(state, _, url) {
            assert.step(`replaceState ${url}`);
            return super.pushState(state, _, url);
        },
    });
};

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
        patchWithCleanup(browser.location, {
            origin: "http://example.com",
        });
        redirect("/odoo");
        startRouter();
    });

    QUnit.module("Load State: new urls");

    QUnit.test("action loading", async (assert) => {
        redirect("/odoo/action-1001");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App1");
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1001",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("menu loading", async (assert) => {
        redirect("/odoo?menu_id=2");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1002",
            "url now points to the default action of the menu"
        );
        assert.verifySteps(["pushState http://example.com/odoo/action-1002"]);
    });

    QUnit.test("action and menu loading", async (assert) => {
        redirect("/odoo/action-1001?menu_id=2");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        assert.deepEqual(router.current, {
            action: 1001,
            actionStack: [
                {
                    action: 1001,
                    displayName: "Client action 1001",
                },
            ],
        });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1001",
            "menu is removed from url"
        );
        assert.verifySteps(["pushState http://example.com/odoo/action-1001"]);
    });

    QUnit.test("initial loading with action id", async (assert) => {
        redirect("/odoo/action-1001");
        logHistoryInteractions(assert);
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/action/load", "/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1001",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("initial loading with action tag", async (assert) => {
        redirect("/odoo/__test__client__action__");
        logHistoryInteractions(assert);
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/__test__client__action__",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("fallback on home action if no action found", async (assert) => {
        logHistoryInteractions(assert);
        patchUserWithCleanup({ homeActionId: 1001 });

        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1001");
        assert.verifySteps(["pushState http://example.com/odoo/action-1001"]);
        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").innerText, "App1");
    });

    QUnit.test("correctly sends additional context", async (assert) => {
        // %2C is a URL-encoded comma
        redirect("/odoo/4/action-1001?active_ids=4%2C8");
        logHistoryInteractions(assert);
        function mockRPC(route, params) {
            if (route === "/web/action/load") {
                assert.deepEqual(params, {
                    action_id: 1001,
                    context: {
                        active_id: 4, // aditional context
                        active_ids: [4, 8], // aditional context
                        lang: "en", // user context
                        tz: "taht", // user context
                        uid: 7, // user context
                    },
                });
            }
        }
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/4/action-1001?active_ids=4%2C8",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("supports action as xmlId", async (assert) => {
        redirect("/odoo/action-wowl.client_action");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_xmlId"
        );
        assert.containsNone(target, ".o_menu_brand");
        assert.strictEqual(
            browser.location.href,
            // FIXME should we canonicalize the URL? If yes, shouldn't we use the client action tag instead?
            "http://example.com/odoo/action-1099",
            "url did not change"
        );
        assert.verifySteps(["pushState http://example.com/odoo/action-1099"]);
    });

    QUnit.test("supports opening action in dialog", async (assert) => {
        serverData.actions["wowl.client_action"].target = "new";
        // FIXME this is super weird: we open an action in target new from the url?
        redirect("/odoo/action-wowl.client_action");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.containsOnce(target, ".test_client_action");
        assert.containsOnce(target, ".modal .test_client_action");
        assert.containsNone(target, ".o_menu_brand");
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-wowl.client_action",
            "action in target new doesn't affect the URL"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("should not crash on invalid state", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/m-partner?view_type=list");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual($(target).text(), "", "should display nothing");
        assert.verifySteps(["/web/webclient/load_menus"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/m-partner?view_type=list",
            "the url did not change"
        );
        assert.verifySteps(
            [],
            "No default action was found, no action controller was mounted: pushState not called"
        );
    });

    QUnit.test("properly load client actions", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/HelloWorldTest",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("properly load client actions with path", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static path = "my-action";
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.deepEqual(router.current, {
            action: "my-action",
            actionStack: [
                {
                    action: "my-action",
                    displayName: "",
                },
            ],
        });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "pushState http://example.com/odoo/my-action",
        ]);
        assert.strictEqual(browser.location.href, "http://example.com/odoo/my-action");
    });

    QUnit.test("properly load client actions with resId", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };

            setup() {
                assert.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/HelloWorldTest/12");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus", "resId:12"]);
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        assert.deepEqual(getBreadCrumbTexts(target), ["Client Action DisplayName"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/HelloWorldTest/12",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("properly load client actions with updateResId", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };

            setup() {
                onMounted(() => {
                    this.props.updateResId(12);
                });
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/HelloWorldTest");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "pushState http://example.com/odoo/HelloWorldTest/12",
        ]);
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        assert.deepEqual(getBreadCrumbTexts(target), ["Client Action DisplayName"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/HelloWorldTest/12",
            "the url did change (the resId was added)"
        );
    });

    QUnit.test("properly load client actions with resId and path (1)", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };
            static path = "my_client";

            setup() {
                assert.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/HelloWorldTest/12");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "resId:12",
            "pushState http://example.com/odoo/my_client/12", // initial pushState to update the url with the correct path
        ]);
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        assert.deepEqual(getBreadCrumbTexts(target), ["Client Action DisplayName"]);
        assert.strictEqual(browser.location.href, "http://example.com/odoo/my_client/12");
        assert.verifySteps([], "pushState was not called"); // no pushState should be called after the initial one
    });

    QUnit.test("properly load client actions with resId and path (2)", async function (assert) {
        class ClientAction extends Component {
            static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
            static displayName = "Client Action DisplayName";
            static components = { ControlPanel };
            static path = "my_client";

            setup() {
                assert.step("resId:" + this.props.resId);
            }
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/my_client/12");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus", "resId:12"]);
        // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
        assert.deepEqual(getBreadCrumbTexts(target), ["Client Action DisplayName"]);
        assert.strictEqual(browser.location.href, "http://example.com/odoo/my_client/12");
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test(
        "properly load client actions with LazyTranslatedString displayName",
        async function (assert) {
            class ClientAction extends Component {
                static template = xml`<ControlPanel/><div class="o_client_action_test">Hello World</div>`;
                static props = ["*"];
                static displayName = _t("translatable displayname");
                static components = { ControlPanel };
                static path = "my_client";
            }
            actionRegistry.add("HelloWorldTest", ClientAction);
            const mockRPC = async function (route, { method }) {
                assert.step(method || route);
            };
            redirect("/odoo/my_client");
            logHistoryInteractions(assert);
            await createWebClient({ serverData, mockRPC });
            assert.strictEqual(
                $(target).find(".o_client_action_test").text(),
                "Hello World",
                "should have correctly rendered the client action"
            );
            assert.verifySteps(["/web/webclient/load_menus"]);
            // Breadcrumb should have only one item, the client action don't have a LazyController (a multi-record view)
            assert.deepEqual(getBreadCrumbTexts(target), ["translatable displayname"]);
            assert.strictEqual(browser.location.href, "http://example.com/odoo/my_client");
            assert.verifySteps([], "pushState was not called");
        }
    );

    QUnit.test("properly load act window actions", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/action-1");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_control_panel");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
        ]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("properly load records", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/m-partner/2");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/m-partner/2",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("properly load records with existing first APP", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        // simulate a real scenario with a first app (e.g. Discuss), to ensure that we don't
        // fallback on that first app when only a model and res_id are given in the url
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
            2: { id: 2, children: [], name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
        };
        redirect("/odoo/m-partner/2");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.containsNone(target, ".o_menu_brand");
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/m-partner/2",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("properly load default record", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/action-3/new");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "onchange",
        ]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-3/new",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("load requested view for act window actions", async function (assert) {
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/odoo/action-3?view_type=kanban");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
        ]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-3?view_type=kanban",
            "the url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test(
        "lazy load multi record view if mono record one is requested",
        async function (assert) {
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "unity_read") {
                    assert.step(`unity_read ${kwargs.method}`);
                } else {
                    assert.step(method || route);
                }
            };
            redirect("/odoo/action-3/2");
            logHistoryInteractions(assert);
            await createWebClient({ serverData, mockRPC });
            assert.containsNone(target, ".o_list_view");
            assert.containsOnce(target, ".o_form_view");
            assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "Second record"]);
            assert.strictEqual(
                browser.location.href,
                "http://example.com/odoo/action-3/2",
                "the url did not change"
            );
            assert.verifySteps(
                ["/web/action/load", "/web/webclient/load_menus", "get_views", "web_read"],
                "pushState was not called"
            );
            // go back to List
            await click(target.querySelector(".o_control_panel .breadcrumb a"));
            assert.containsOnce(target, ".o_list_view");
            assert.containsNone(target, ".o_form_view");
            assert.verifySteps(["web_search_read"]);
            await nextTick(); // pushState is debounced
            assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3");
            assert.verifySteps(["pushState http://example.com/odoo/action-3"]);
        }
    );

    QUnit.test("go back with breadcrumbs after doAction", async function (assert) {
        logHistoryInteractions(assert);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        await nextTick(); // pushState is debounced
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        assert.verifySteps(["pushState http://example.com/odoo/action-4"]);
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        await doAction(webClient, 3, {
            props: { resId: 2 },
            viewType: "form",
        });
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4", "Second record"]);
        await nextTick(); // pushState is debounced
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4/action-3/2");
        assert.verifySteps(
            ["pushState http://example.com/odoo/action-4/action-3/2"],
            "pushState was called only once"
        );
        // go back to previous action
        await click(target.querySelector(".o_control_panel .breadcrumb .o_back_button a"));
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        await nextTick(); // pushState is debounced
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        assert.verifySteps(["pushState http://example.com/odoo/action-4"]);
    });

    QUnit.test(
        "lazy loaded multi record view with failing mono record one",
        async function (assert) {
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "web_read") {
                    return Promise.reject();
                }
            };
            redirect("/odoo/action-3/2");
            logHistoryInteractions(assert);
            const webClient = await createWebClient({ serverData, mockRPC });
            assert.containsNone(target, ".o_form_view");
            assert.containsOnce(target, ".o_list_view"); // Show the lazy loaded list view
            assert.strictEqual(
                browser.location.href,
                "http://example.com/odoo/action-3",
                "url reflects that we are not on the failing record"
            );
            assert.verifySteps(["pushState http://example.com/odoo/action-3"]);
            await doAction(webClient, 1);
            assert.containsOnce(target, ".o_kanban_view");
            await nextTick(); // pushState is debounced
            assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3/action-1");
            assert.verifySteps(["pushState http://example.com/odoo/action-3/action-1"]);
        }
    );

    QUnit.test("should push the correct state at the right time", async function (assert) {
        // formerly "should not push a loaded state"
        redirect("/odoo/action-3");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.deepEqual(router.current, {
            action: 3,
            actionStack: [
                {
                    action: 3,
                },
            ],
        });
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3");
        assert.verifySteps([], "loading the initial state shouldn't push the state");
        await click(target.querySelector("tr .o_data_cell"));
        await nextTick(); // pushState is debounced
        assert.deepEqual(router.current, {
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
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3/1");
        assert.verifySteps(
            ["pushState http://example.com/odoo/action-3/1"],
            "should push the state if it changes afterwards"
        );
    });

    QUnit.test("load state supports being given menu_id alone", async function (assert) {
        serverData.menus[666] = {
            id: 666,
            children: [],
            name: "App1",
            appID: 1,
            actionID: 1,
        };
        const mockRPC = async function (route) {
            assert.step(route);
        };
        redirect("/odoo?menu_id=666");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
            "pushState http://example.com/odoo/action-1",
        ]);
    });

    QUnit.test("load state: in a form view, no id in initial state", async function (assert) {
        serverData.actions[999] = {
            id: 999,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [666, "form"],
            ],
        };
        const mockRPC = async (route) => {
            assert.step(route);
        };
        redirect("/odoo/action-999/new");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partner", "New"]);
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/onchange",
        ]);
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-999/new");
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test("load state: in a form view, wrong id in the state", async function (assert) {
        registry.category("services").add("error", errorService);
        serverData.actions[1000] = {
            id: 1000,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };
        redirect("/odoo/action-1000/999");
        logHistoryInteractions(assert);
        await createWebClient({ serverData });
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_notification_body", 1, "should have a notification");
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1000",
            "url reflects that we are not on the record"
        );
        assert.verifySteps(["pushState http://example.com/odoo/action-1000"]);
    });

    QUnit.test("server action loading with id", async (assert) => {
        serverData.actions[2].path = "my_action";
        serverData.actions[2].code = () => {
            return {
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            };
        };
        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                assert.step(`action: ${args.action_id}`);
            }
        };
        redirect("/odoo/my_action/2");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.deepEqual(getBreadCrumbTexts(target), ["Partner", "Second record"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/my_action/2",
            "url did not change"
        );
        await click(target.querySelector(".o_control_panel .breadcrumb-item"));
        assert.containsOnce(target, ".o_list_view");

        assert.verifySteps(["action: my_action"], "/web/action/load is called only once");
        await nextTick(); // pushState is debounced
        assert.verifySteps(["pushState http://example.com/odoo/my_action"]);
    });

    QUnit.test("state with integer active_ids should not crash", async function (assert) {
        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                assert.step(
                    `action: ${args.action_id}, active_ids: ${JSON.stringify(
                        args.context.active_ids
                    )}`
                );
            }
        };
        redirect("/odoo/action-2?active_ids=3");
        logHistoryInteractions(assert);
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-2?active_ids=3",
            "url did not change"
        );
        assert.verifySteps(["action: 2, active_ids: [3]"], "pushState was not called");
    });

    QUnit.test(
        "load a form view via url, then switch to view list, the search view is correctly initialized",
        async function (assert) {
            serverData.views = {
                ...serverData.views,
                "partner,false,search": `
                    <search>
                        <filter name="filter" string="Filter" domain="[('foo', '=', 'yop')]"/>
                    </search>
                `,
            };

            redirect("/odoo/action-3/new");
            logHistoryInteractions(assert);
            await createWebClient({ serverData });
            assert.strictEqual(
                browser.location.href,
                "http://example.com/odoo/action-3/new",
                "url did not change"
            );
            assert.verifySteps([], "pushState was not called");

            await click(target.querySelector(".o_control_panel .breadcrumb-item"));

            assert.containsN(target, ".o_list_view .o_data_row", 5);

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Filter");

            assert.containsN(target, ".o_list_view .o_data_row", 1);
            await nextTick(); // pushState is debounced
            assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3");
            assert.verifySteps(["pushState http://example.com/odoo/action-3"]);
        }
    );

    QUnit.test("initial action crashes", async (assert) => {
        assert.expectErrors();

        redirect("/odoo/__test__client__action__?menu_id=1");
        logHistoryInteractions(assert);
        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                assert.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        registry.category("services").add("error", errorService);

        await createWebClient({ serverData });
        assert.verifySteps(["clientAction setup"]);
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/__test__client__action__?menu_id=1",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
        await nextTick();
        assert.expectErrors(["my error"]);
        assert.containsOnce(target, ".o_error_dialog");
        await click(target, ".modal-header .btn-close");
        assert.containsNone(target, ".o_error_dialog");
        await click(target, "nav .o_navbar_apps_menu .dropdown-toggle ");
        assert.containsN(target, ".dropdown-item.o_app", 3);
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, "");
        await nextTick(); // pushState is debounced
        assert.deepEqual(router.current, {
            action: "__test__client__action__",
            menu_id: 1,
            actionStack: [
                {
                    action: "__test__client__action__",
                },
            ],
        });
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/__test__client__action__?menu_id=1",
            "url did not change"
        );
        assert.verifySteps([], "pushState was not called");
    });

    QUnit.test(
        "initial loading with multiple path segments loads the breadcrumbs",
        async (assert) => {
            redirect("/odoo/partners/2/action-28/1");
            logHistoryInteractions(assert);
            setupWebClientRegistries();

            const mockRPC = (route) => assert.step(route);
            const env = await makeTestEnv({ serverData, mockRPC });

            assert.verifySteps(["/web/action/load", "/web/webclient/load_menus"]);

            await mount(WebClient, getFixture(), { env });
            await nextTick();
            assert.strictEqual(
                browser.location.href,
                "http://example.com/odoo/partners/2/action-28/1",
                "url did not change"
            );
            assert.verifySteps(
                [
                    "/web/action/load_breadcrumbs",
                    "/web/dataset/call_kw/partner/get_views",
                    "/web/dataset/call_kw/partner/web_read",
                ],
                "pushState was not called"
            );
            await click(target, ".breadcrumb .dropdown-toggle");
            const breadcrumbs = [
                document.body.querySelector(".o-overlay-container .dropdown-menu").textContent,
                ...getBreadCrumbTexts(target).slice(1),
            ];
            assert.deepEqual(breadcrumbs, [
                "Partners Action 27",
                "Second record",
                "Partners Action 28",
                "First record",
            ]);
            assert.verifySteps([]);
        }
    );

    QUnit.module("Load State: legacy urls");

    QUnit.test("action loading", async (assert) => {
        assert.expect(2);
        redirect("/web#action=1001");
        await createWebClient({ serverData });
        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App1");
    });

    QUnit.test("menu loading", async (assert) => {
        assert.expect(2);
        redirect("/web#menu_id=2");
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("action and menu loading", async (assert) => {
        assert.expect(3);
        redirect("/web#action=1001&menu_id=2");
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        assert.deepEqual(router.current, {
            action: 1001,
            actionStack: [
                {
                    action: 1001,
                    displayName: "Client action 1001",
                },
            ],
        });
    });

    QUnit.test("initial loading with action id", async (assert) => {
        assert.expect(4);
        redirect("/web#action=1001");
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/action/load", "/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("initial loading with action tag", async (assert) => {
        assert.expect(3);
        redirect("/web#action=__test__client__action__");
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("correctly sends additional context", async (assert) => {
        assert.expect(1);
        redirect("/web#action=1001&active_id=4&active_ids=4,8");
        function mockRPC(route, params) {
            if (route === "/web/action/load") {
                assert.deepEqual(params, {
                    action_id: 1001,
                    context: {
                        active_id: 4, // aditional context
                        active_ids: [4, 8], // aditional context
                        lang: "en", // user context
                        tz: "taht", // user context
                        uid: 7, // user context
                    },
                });
            }
        }
        await createWebClient({ serverData, mockRPC });
    });

    QUnit.test("supports action as xmlId", async (assert) => {
        assert.expect(2);
        redirect("/web#action=wowl.client_action");
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_xmlId"
        );
        assert.containsNone(target, ".o_menu_brand");
    });

    QUnit.test("supports opening action in dialog", async (assert) => {
        assert.expect(3);
        serverData.actions["wowl.client_action"].target = "new";
        redirect("/web#action=wowl.client_action");
        await createWebClient({ serverData });
        assert.containsOnce(target, ".test_client_action");
        assert.containsOnce(target, ".modal .test_client_action");
        assert.containsNone(target, ".o_menu_brand");
    });

    QUnit.test("should not crash on invalid state", async function (assert) {
        assert.expect(3);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#res_model=partner");
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual($(target).text(), "", "should display nothing");
        assert.verifySteps(["/web/webclient/load_menus"]);
    });

    QUnit.test("properly load client actions", async function (assert) {
        assert.expect(3);
        class ClientAction extends Component {
            static template = xml`<div class="o_client_action_test">Hello World</div>`;
            static props = ["*"];
        }
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#action=HelloWorldTest");
        await createWebClient({ serverData, mockRPC });
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus"]);
    });

    QUnit.test("properly load act window actions", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#action=1");
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_control_panel");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("properly load records", async function (assert) {
        assert.expect(6);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#id=2&model=partner");
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
    });

    QUnit.test("properly load records with existing first APP", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        // simulate a real scenario with a first app (e.g. Discuss), to ensure that we don't
        // fallback on that first app when only a model and res_id are given in the url
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
            2: { id: 2, children: [], name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
        };
        redirect("/web#id=2&model=partner");
        await createWebClient({ serverData, mockRPC });

        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.containsNone(target, ".o_menu_brand");
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
    });

    QUnit.test("properly load default record", async function (assert) {
        assert.expect(6);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#action=3&id=&model=partner&view_type=form");
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "onchange",
        ]);
    });

    QUnit.test("load requested view for act window actions", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        redirect("/web#action=3&view_type=kanban");
        await createWebClient({ serverData, mockRPC });
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test(
        "lazy load multi record view if mono record one is requested",
        async function (assert) {
            assert.expect(11);
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "unity_read") {
                    assert.step(`unity_read ${kwargs.method}`);
                } else {
                    assert.step(method || route);
                }
            };
            redirect("/web#action=3&id=2&view_type=form");
            await createWebClient({ serverData, mockRPC });
            assert.containsNone(target, ".o_list_view");
            assert.containsOnce(target, ".o_form_view");
            assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "Second record"]);
            // go back to List
            await click(target.querySelector(".o_control_panel .breadcrumb a"));
            assert.containsOnce(target, ".o_list_view");
            assert.containsNone(target, ".o_form_view");
            assert.verifySteps([
                "/web/action/load",
                "/web/webclient/load_menus",
                "get_views",
                "web_read",
                "web_search_read",
            ]);
        }
    );

    QUnit.test(
        "lazy loaded multi record view with failing mono record one",
        async function (assert) {
            assert.expect(3);
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "web_read") {
                    return Promise.reject();
                }
            };
            redirect("/web#action=3&id=2&view_type=form");
            const webClient = await createWebClient({ serverData, mockRPC });
            assert.containsNone(target, ".o_form_view");
            assert.containsOnce(target, ".o_list_view"); // Show the lazy loaded list view
            await doAction(webClient, 1);
            assert.containsOnce(target, ".o_kanban_view");
        }
    );

    QUnit.test("should push the correct state at the right time", async function (assert) {
        // formerly "should not push a loaded state"
        const pushState = browser.history.pushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    pushState(...arguments);
                    assert.step("push_state");
                },
            }),
        });
        redirect("/web#action=3");
        await createWebClient({ serverData });
        let currentState = router.current;
        assert.deepEqual(currentState, {
            action: 3,
            actionStack: [
                {
                    action: 3,
                },
            ],
        });
        assert.verifySteps([], "loading the initial state shouldn't push the state");
        await click(target.querySelector("tr .o_data_cell"));
        await nextTick();
        currentState = router.current;
        assert.deepEqual(currentState, {
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
        assert.verifySteps(["push_state"], "should push the state of it changes afterwards");
    });

    QUnit.test("load state supports being given menu_id alone", async function (assert) {
        assert.expect(7);
        serverData.menus[666] = {
            id: 666,
            children: [],
            name: "App1",
            appID: 1,
            actionID: 1,
        };
        const mockRPC = async function (route) {
            assert.step(route);
        };
        redirect("/web#menu_id=666");
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
        ]);
    });

    QUnit.test("load state: in a form view, no id in initial state", async function (assert) {
        assert.expect(8);
        serverData.actions[999] = {
            id: 999,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [666, "form"],
            ],
        };
        const mockRPC = async (route) => {
            assert.step(route);
        };
        redirect("/web#action=999&view_type=form&id=");
        await createWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partner", "New"]);
        assert.verifySteps([
            "/web/action/load",
            "/web/webclient/load_menus",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/onchange",
        ]);
        assert.containsOnce(target, ".o_form_view .o_form_editable");
    });

    QUnit.test("load state: in a form view, wrong id in the state", async function (assert) {
        registry.category("services").add("error", errorService);
        serverData.actions[1000] = {
            id: 1000,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };
        redirect("/web#action=1000&view_type=form&id=999");
        await createWebClient({ serverData });
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_notification_body", 1, "should have a notification");
    });

    QUnit.test("state with integer active_ids should not crash", async function (assert) {
        assert.expect(2);

        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                assert.strictEqual(args.action_id, 2);
                assert.deepEqual(args.context.active_ids, [3]);
            }
        };
        redirect("/web#action=2&active_ids=3");
        await createWebClient({ serverData, mockRPC });
    });

    QUnit.test(
        "charge a form view via url, then switch to view list, the search view is correctly initialized",
        async function (assert) {
            assert.expect(2);

            serverData.views = {
                ...serverData.views,
                "partner,false,search": `
                    <search>
                        <filter name="filter" string="Filter" domain="[('foo', '=', 'yop')]"/>
                    </search>
                `,
            };

            redirect("/web#action=3&model=partner&view_type=form");
            await createWebClient({ serverData });

            await click(target.querySelector(".o_control_panel .breadcrumb-item"));

            assert.containsN(target, ".o_list_view .o_data_row", 5);

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Filter");

            assert.containsN(target, ".o_list_view .o_data_row", 1);
        }
    );

    QUnit.test("initial action crashes", async (assert) => {
        assert.expect(8);
        assert.expectErrors();

        redirect("/web#action=__test__client__action__&menu_id=1");
        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                assert.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        registry.category("services").add("error", errorService);

        await createWebClient({ serverData });
        assert.verifySteps(["clientAction setup"]);
        await nextTick();
        assert.expectErrors(["my error"]);
        assert.containsOnce(target, ".o_error_dialog");
        await click(target, ".modal-header .btn-close");
        assert.containsNone(target, ".o_error_dialog");
        await click(target, "nav .o_navbar_apps_menu .dropdown-toggle ");
        assert.containsN(target, ".dropdown-item.o_app", 3);
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App1");
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, "");
        assert.deepEqual(router.current, {
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
