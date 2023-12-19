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
import { router } from "@web/core/browser/router";

import { Component, xml } from "@odoo/owl";

function getBreadCrumbTexts(target) {
    return getNodesTextContent(target.querySelectorAll(".breadcrumb-item, .o_breadcrumb .active"));
}

let serverData;
let target;

const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Load State");

    QUnit.test("action loading", async (assert) => {
        assert.expect(2);
        Object.assign(browser.location, { search: "action=1001" });
        await createWebClient({ serverData });
        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App1");
    });

    QUnit.test("menu loading", async (assert) => {
        assert.expect(2);
        Object.assign(browser.location, { search: "menu_id=2" });
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("action and menu loading", async (assert) => {
        assert.expect(3);
        Object.assign(browser.location, { search: "action=1001&menu_id=2" });
        await createWebClient({ serverData });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        assert.deepEqual(router.current, {
            action: 1001,
            menu_id: 2,
        });
    });

    QUnit.test("initial loading with action id", async (assert) => {
        assert.expect(4);
        const search = "?action=1001";
        Object.assign(browser.location, { search });
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/action/load", "/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("initial loading with action tag", async (assert) => {
        assert.expect(3);
        const search = "?action=__test__client__action__";
        Object.assign(browser.location, { search });
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("fallback on home action if no action found", async (assert) => {
        assert.expect(2);
        patchUserWithCleanup({ homeActionId: 1001 });

        await createWebClient({ serverData });
        await nextTick(); // wait for the navbar to be updated
        await nextTick(); // wait for the action to be displayed

        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").innerText, "App1");
    });

    QUnit.test("correctly sends additional context", async (assert) => {
        assert.expect(1);
        const search = "?action=1001&active_id=4&active_ids=4,8";
        Object.assign(browser.location, { search });
        function mockRPC(route, params) {
            if (route === "/web/action/load") {
                assert.deepEqual(params, {
                    action_id: 1001,
                    additional_context: {
                        active_id: 4,
                        active_ids: [4, 8],
                    },
                });
            }
        }
        await createWebClient({ serverData, mockRPC });
    });

    QUnit.test("supports action as xmlId", async (assert) => {
        assert.expect(2);
        Object.assign(browser.location, { search: "action=wowl.client_action" });
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
        Object.assign(browser.location, { search: "action=wowl.client_action" });
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
        Object.assign(browser.location, { search: "res_model=partner" });
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
        Object.assign(browser.location, { search: "action=HelloWorldTest" });
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
        Object.assign(browser.location, { search: "action=1" });
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
        Object.assign(browser.location, { search: "id=2&model=partner" });
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
        const search = "?id=2&model=partner";
        Object.assign(browser.location, { search });
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
        Object.assign(browser.location, { search: "action=3&id=&model=partner&view_type=form" });
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
        Object.assign(browser.location, { search: "action=3&view_type=kanban" });
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
            Object.assign(browser.location, { search: "action=3&id=2&view_type=form" });
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

    QUnit.test("lazy load multi record view with previous action", async function (assert) {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        await doAction(webClient, 3, {
            props: { resId: 2 },
            viewType: "form",
        });
        assert.deepEqual(getBreadCrumbTexts(target), [
            "Partners Action 4",
            "Partners",
            "Second record",
        ]);
        // go back to List
        await click(target.querySelector(".o_control_panel .breadcrumb .o_back_button a"));
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4", "Partners"]);
    });

    QUnit.test(
        "lazy loaded multi record view with failing mono record one",
        async function (assert) {
            assert.expect(3);
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "web_read") {
                    return Promise.reject();
                }
            };
            Object.assign(browser.location, { search: "action=3&id=2&view_type=form" });
            const webClient = await createWebClient({ serverData, mockRPC });
            assert.containsNone(target, ".o_form_view");
            assert.containsNone(target, ".o_list_view");
            await doAction(webClient, 1);
            assert.containsOnce(target, ".o_kanban_view");
        }
    );

    QUnit.test("should push the correct state at the right time", async function (assert) {
        // formerly "should not push a loaded state"
        assert.expect(6);
        const pushState = browser.history.pushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    pushState(...arguments);
                    assert.step("push_state");
                },
            }),
        });
        Object.assign(browser.location, { search: "action=3" });
        await createWebClient({ serverData });
        let currentState = router.current;
        assert.deepEqual(currentState, {
            action: 3,
            model: "partner",
            view_type: "list",
        });
        assert.verifySteps(["push_state"], "should have pushed the final state");
        await click(target.querySelector("tr .o_data_cell"));
        await nextTick();
        currentState = router.current;
        assert.deepEqual(currentState, {
            action: 3,
            id: 1,
            model: "partner",
            view_type: "form",
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
        Object.assign(browser.location, { search: "menu_id=666" });
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
        Object.assign(browser.location, { search: "action=999&view_type=form&id=" });
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
        serverData.actions[1000] = {
            id: 1000,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            view_type: "form",
            res_id: 999,
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1000);
        assert.containsOnce(target, ".o_list_view");
    });

    QUnit.test("state with integer active_ids should not crash", async function (assert) {
        assert.expect(2);

        const mockRPC = async (route, args) => {
            if (route === "/web/action/run") {
                assert.strictEqual(args.action_id, 2);
                assert.deepEqual(args.context.active_ids, [3]);
                return new Promise(() => {});
            }
        };
        Object.assign(browser.location, { search: "action=2&active_ids=3" });
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

            Object.assign(browser.location, { search: "action=3&model=partner&view_type=form" });
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

        Object.assign(browser.location, { search: "?action=__test__client__action__&menu_id=1" });
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
        assert.containsNone(target, ".o_menu_brand");
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, "");
        assert.deepEqual(router.current, {
            action: "__test__client__action__",
            menu_id: 1,
        });
    });
});
