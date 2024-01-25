/** @odoo-module alias=@web/../tests/webclient/actions/push_state_tests default=false */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";
import { click, getFixture, makeDeferred, nextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

import { Component, xml } from "@odoo/owl";

let serverData;
let target;
const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Push State");

    QUnit.test("basic action as App", async (assert) => {
        assert.expect(5);
        await createWebClient({ serverData });
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o_navbar_apps_menu .dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1002);
        assert.strictEqual(urlState.menu_id, 2);
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("do action keeps menu in url", async (assert) => {
        assert.expect(9);
        const webClient = await createWebClient({ serverData });
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o_navbar_apps_menu .dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1002);
        assert.strictEqual(urlState.menu_id, 2);
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        await doAction(webClient, 1001, { clearBreadcrumbs: true });
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1001);
        assert.strictEqual(urlState.menu_id, 2);
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("actions can push state", async (assert) => {
        assert.expect(5);
        class ClientActionPushes extends Component {
            static template = xml`
                <div class="test_client_action" t-on-click="_actionPushState">
                    ClientAction_<t t-esc="props.params and props.params.description" />
                </div>`;
            static props = ["*"];
            _actionPushState() {
                router.pushState({ arbitrary: "actionPushed" });
            }
        }
        actionRegistry.add("client_action_pushes", ClientActionPushes);
        const webClient = await createWebClient({ serverData });
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.menu_id, undefined);
        await click(target, ".test_client_action");
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.arbitrary, "actionPushed");
    });

    QUnit.test("actions override previous state", async (assert) => {
        assert.expect(5);
        class ClientActionPushes extends Component {
            static template = xml`
                <div class="test_client_action" t-on-click="_actionPushState">
                    ClientAction_<t t-esc="props.params and props.params.description" />
                </div>`;
            static props = ["*"];
            _actionPushState() {
                router.pushState({ arbitrary: "actionPushed" });
            }
        }
        actionRegistry.add("client_action_pushes", ClientActionPushes);
        const webClient = await createWebClient({ serverData });
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await click(target, ".test_client_action");
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.arbitrary, "actionPushed");
        await doAction(webClient, 1001);
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1001);
        assert.strictEqual(urlState.arbitrary, undefined);
    });

    QUnit.test("actions override previous state from menu click", async (assert) => {
        assert.expect(3);
        class ClientActionPushes extends Component {
            static template = xml`
                <div class="test_client_action" t-on-click="_actionPushState">
                    ClientAction_<t t-esc="props.params and props.params.description" />
                </div>`;
            static props = ["*"];
            _actionPushState() {
                router.pushState({ arbitrary: "actionPushed" });
            }
        }
        actionRegistry.add("client_action_pushes", ClientActionPushes);
        const webClient = await createWebClient({ serverData });
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await click(target, ".test_client_action");
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o_navbar_apps_menu .dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1002);
        assert.strictEqual(urlState.menu_id, 2);
    });

    QUnit.test("action in target new do not push state", async (assert) => {
        assert.expect(1);
        serverData.actions[1001].target = "new";
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    throw new Error("should not push state");
                },
            }),
        });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1001);
        assert.containsOnce(target, ".modal .test_client_action");
        await nextTick();
    });

    QUnit.test("properly push state", async function (assert) {
        assert.expect(3);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        await nextTick();
        assert.deepEqual(router.current, {
            action: 4,
            model: "partner",
            view_type: "kanban",
        });
        await doAction(webClient, 8);
        await nextTick();
        assert.deepEqual(router.current, {
            action: 8,
            model: "pony",
            view_type: "list",
        });
        await testUtils.dom.click($(target).find("tr .o_data_cell:first"));
        await nextTick();
        assert.deepEqual(router.current, {
            action: 8,
            model: "pony",
            view_type: "form",
            id: 4,
        });
    });

    QUnit.test("push state after action is loaded, not before", async function (assert) {
        const def = makeDeferred();
        const mockRPC = async function (route, args) {
            if (args.method === "web_search_read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        doAction(webClient, 4);
        await nextTick();
        await nextTick();
        assert.deepEqual(router.current, {});
        def.resolve();
        await nextTick();
        await nextTick();
        assert.deepEqual(router.current, {
            action: 4,
            model: "partner",
            view_type: "kanban",
        });
    });

    QUnit.test("do not push state when action fails", async function (assert) {
        assert.expect(3);
        const mockRPC = async function (route, args) {
            if (args && args.method === "read") {
                return Promise.reject();
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 8);
        await nextTick();
        assert.deepEqual(router.current, {
            action: 8,
            model: "pony",
            view_type: "list",
        });
        await testUtils.dom.click($(target).find("tr.o_data_row:first"));
        // we make sure here that the list view is still in the dom
        assert.containsOnce(target, ".o_list_view", "there should still be a list view in dom");
        await nextTick();
        assert.deepEqual(router.current, {
            action: 8,
            model: "pony",
            view_type: "list",
        });
    });
});
