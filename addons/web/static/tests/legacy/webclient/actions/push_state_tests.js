/** @odoo-module alias=@web/../tests/webclient/actions/push_state_tests default=false */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { router, startRouter } from "@web/core/browser/router";
import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";
import { click, getFixture, makeDeferred, nextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

import { Component, xml } from "@odoo/owl";
import { redirect } from "@web/core/utils/urls";
import {
    editSearch,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/legacy/search/helpers";

let serverData;
let target;
const actionRegistry = registry.category("actions");

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

    QUnit.module("Push State");

    QUnit.test("basic action as App", async (assert) => {
        await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o-dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        urlState = router.current;
        assert.strictEqual(urlState.action, 1002);
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1002");
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("do action keeps menu in url", async (assert) => {
        const webClient = await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o-dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        urlState = router.current;
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1002");
        assert.strictEqual(urlState.action, 1002);
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        await doAction(webClient, 1001, { clearBreadcrumbs: true });
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1001");
        urlState = router.current;
        assert.strictEqual(urlState.action, 1001);
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("actions can push state", async (assert) => {
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
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/client_action_pushes"
        );
        assert.strictEqual(browser.history.length, 2);
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.menu_id, undefined);
        await click(target, ".test_client_action");
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/client_action_pushes?arbitrary=actionPushed"
        );
        assert.strictEqual(browser.history.length, 3);
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.arbitrary, "actionPushed");
    });

    QUnit.test("actions override previous state", async (assert) => {
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
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await nextTick(); // wait for pushState because it's unrealistic to click before it
        await click(target, ".test_client_action");
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/client_action_pushes?arbitrary=actionPushed"
        );
        assert.strictEqual(browser.history.length, 3); // Two history entries
        urlState = router.current;
        assert.strictEqual(urlState.action, "client_action_pushes");
        assert.strictEqual(urlState.arbitrary, "actionPushed");
        await doAction(webClient, 1001);
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-1001",
            "client_action_pushes removed from url because action 1001 is in target main"
        );
        assert.strictEqual(browser.history.length, 4);
        urlState = router.current;
        assert.strictEqual(urlState.action, 1001);
        assert.strictEqual(urlState.arbitrary, undefined);
    });

    QUnit.test("actions override previous state from menu click", async (assert) => {
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
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        let urlState = router.current;
        assert.deepEqual(urlState, {});
        await doAction(webClient, "client_action_pushes");
        await click(target, ".test_client_action");
        await click(target, ".o_navbar_apps_menu button");
        await click(target, ".o-dropdown-item:nth-child(3)");
        await nextTick();
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-1002");
        urlState = router.current;
        assert.strictEqual(urlState.action, 1002);
    });

    QUnit.test("action in target new do not push state", async (assert) => {
        serverData.actions[1001].target = "new";
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    throw new Error("should not push state");
                },
            }),
        });
        const webClient = await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        await doAction(webClient, 1001);
        assert.containsOnce(target, ".modal .test_client_action");
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo",
            "url did not change"
        );
        assert.strictEqual(browser.history.length, 1, "did not create a history entry");
        assert.deepEqual(router.current, {});
    });

    QUnit.test("properly push state", async function (assert) {
        const webClient = await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        await doAction(webClient, 4);
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
            ],
        });
        await doAction(webClient, 8);
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4/action-8");
        assert.strictEqual(browser.history.length, 3);
        assert.deepEqual(router.current, {
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
        await testUtils.dom.click($(target).find("tr .o_data_cell:first"));
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4/action-8/4");
        assert.strictEqual(browser.history.length, 4);
        assert.deepEqual(router.current, {
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
                {
                    action: 8,
                    displayName: "Twilight Sparkle",
                    resId: 4,
                    view_type: "form",
                },
            ],
            resId: 4,
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
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        doAction(webClient, 4);
        await nextTick();
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        assert.deepEqual(router.current, {});
        def.resolve();
        await nextTick();
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
            ],
        });
    });

    QUnit.test("do not push state when action fails", async function (assert) {
        const mockRPC = async function (route, args) {
            if (args && args.method === "read") {
                return Promise.reject();
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        await doAction(webClient, 8);
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-8");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 8,
            actionStack: [
                {
                    action: 8,
                    displayName: "Favorite Ponies",
                    view_type: "list",
                },
            ],
        });
        await testUtils.dom.click($(target).find("tr.o_data_row:first"));
        // we make sure here that the list view is still in the dom
        assert.containsOnce(target, ".o_list_view", "there should still be a list view in dom");
        await nextTick(); // wait for possible debounced pushState
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-8");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 8,
            actionStack: [
                {
                    action: 8,
                    displayName: "Favorite Ponies",
                    view_type: "list",
                },
            ],
        });
    });

    QUnit.test("view_type is in url when not the default one", async function (assert) {
        const webClient = await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        await doAction(webClient, 3);
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 3,
            actionStack: [
                {
                    action: 3,
                    displayName: "Partners",
                    view_type: "list",
                },
            ],
        });
        assert.containsNone(target, ".breadcrumb");
        await doAction(webClient, 3, { viewType: "kanban" });
        await nextTick();
        assert.strictEqual(
            browser.location.href,
            "http://example.com/odoo/action-3?view_type=kanban"
        );
        assert.strictEqual(browser.history.length, 3, "created a history entry");
        assert.containsOnce(target, ".breadcrumb", "created a breadcrumb entry");
        assert.deepEqual(router.current, {
            action: 3,
            view_type: "kanban", // view_type is on the state when it's not the default one
            actionStack: [
                {
                    action: 3,
                    displayName: "Partners",
                    view_type: "list",
                },
                {
                    action: 3,
                    displayName: "Partners",
                    view_type: "kanban",
                },
            ],
        });
    });

    QUnit.test(
        "switchView pushes the stat but doesn't add to the breadcrumbs",
        async function (assert) {
            const webClient = await createWebClient({ serverData });
            assert.strictEqual(browser.location.href, "http://example.com/odoo");
            assert.strictEqual(browser.history.length, 1);
            await doAction(webClient, 3);
            await nextTick();
            assert.strictEqual(browser.location.href, "http://example.com/odoo/action-3");
            assert.strictEqual(browser.history.length, 2);
            assert.deepEqual(router.current, {
                action: 3,
                actionStack: [
                    {
                        action: 3,
                        displayName: "Partners",
                        view_type: "list",
                    },
                ],
            });
            assert.containsNone(target, ".breadcrumb");
            await webClient.env.services.action.switchView("kanban");
            await nextTick();
            assert.strictEqual(
                browser.location.href,
                "http://example.com/odoo/action-3?view_type=kanban"
            );
            assert.strictEqual(browser.history.length, 3, "created a history entry");
            assert.containsNone(target, ".breadcrumb", "didn't create a breadcrumb entry");
            assert.deepEqual(router.current, {
                action: 3,
                view_type: "kanban", // view_type is on the state when it's not the default one
                actionStack: [
                    {
                        action: 3,
                        displayName: "Partners",
                        view_type: "kanban",
                    },
                ],
            });
        }
    );
    QUnit.test("properly push globalState", async function (assert) {
        const webClient = await createWebClient({ serverData });
        assert.strictEqual(browser.location.href, "http://example.com/odoo");
        assert.strictEqual(browser.history.length, 1);
        await doAction(webClient, 4);
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        assert.strictEqual(browser.history.length, 2);
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
            ],
        });
        // add element on the search Model
        await toggleSearchBarMenu(target);
        await editSearch(target, "blip");
        await validateSearch(target);
        assert.strictEqual(target.querySelector(".o_searchview .o_facet_values").innerText, "blip");
        // open record
        await click(target.querySelector(".o_kanban_record"));
        // Add the globalState on the state before leaving the kanban
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
            ],
            globalState: {
                resIds: [2],
                searchModel:
                    '{"nextGroupId":2,"nextGroupNumber":1,"nextId":2,"query":[{"searchItemId":1,"autocompleteValue":{"label":"blip","operator":"ilike","value":"blip"}}],"searchItems":{"1":{"type":"field","fieldName":"foo","fieldType":"char","description":"Foo","groupId":1,"id":1}},"searchPanelInfo":{"className":"","viewTypes":["kanban","list"],"loaded":false,"shouldReload":true},"sections":[]}',
            },
        });
        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4/2");
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
                {
                    action: 4,
                    displayName: "Second record",
                    resId: 2,
                    view_type: "form",
                },
            ],
            resId: 2,
        });
        // came back using the browser
        browser.history.back(); // Click on back button
        await nextTick();
        // The search Model should be restored
        assert.strictEqual(target.querySelector(".o_searchview .o_facet_values").innerText, "blip");
        assert.strictEqual(browser.location.href, "http://example.com/odoo/action-4");
        // The global state is restored on the state
        assert.deepEqual(router.current, {
            action: 4,
            actionStack: [
                {
                    action: 4,
                    displayName: "Partners Action 4",
                    view_type: "kanban",
                },
            ],
            globalState: {
                resIds: [2],
                searchModel:
                    '{"nextGroupId":2,"nextGroupNumber":1,"nextId":2,"query":[{"searchItemId":1,"autocompleteValue":{"label":"blip","operator":"ilike","value":"blip"}}],"searchItems":{"1":{"type":"field","fieldName":"foo","fieldType":"char","description":"Foo","groupId":1,"id":1}},"searchPanelInfo":{"className":"","viewTypes":["kanban","list"],"loaded":false,"shouldReload":true},"sections":[]}',
            },
        });
    });
});
