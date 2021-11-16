/** @odoo-module **/

import { click, getFixture, makeDeferred } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import {
    isItemSelected,
    toggleFilterMenu,
    toggleMenuItem,
    switchView,
} from "@web/../tests/search/helpers";
import { legacyExtraNextTick, nextTick } from "../../helpers/utils";
import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import { useSetupView } from "@web/views/helpers/view_hook";

const { Component, xml } = owl;
const actionRegistry = registry.category("actions");

let serverData;
let target;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Concurrency management");

    QUnit.skip("drop previous actions if possible", async function (assert) {
        assert.expect(7);
        const def = testUtils.makeTestPromise();
        const mockRPC = async function (route, args) {
            assert.step(route);
            if (route === "/web/action/load") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        doAction(webClient, 4);
        doAction(webClient, 8);
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        // action 4 loads a kanban view first, 6 loads a list view. We want a list
        assert.containsOnce(target, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/action/load",
            "/web/dataset/call_kw/pony/get_views",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("handle switching view and switching back on slow network", async function (assert) {
        // #long-term-skipped-test
        // This scenario isn't supported while we still have the compatibility layer.
        // As soon as the list and kanban views will be written in owl, this test will
        // need to be unskipped.
        assert.expect(9);
        let def = testUtils.makeTestPromise();
        const defs = [Promise.resolve(), def, Promise.resolve()];
        const mockRPC = async function (route, args) {
            assert.step(route);
            if (route === "/web/dataset/search_read") {
                await defs.shift();
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 4);
        // kanban view is loaded, switch to list view
        await switchView(target, "list");
        await legacyExtraNextTick();
        // here, list view is not ready yet, because def is not resolved
        // switch back to kanban view
        await switchView(target, "kanban");
        await legacyExtraNextTick();
        // here, we want the kanban view to reload itself, regardless of list view
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/search_read",
            "/web/dataset/search_read",
            "/web/dataset/search_read",
        ]);
        // we resolve def => list view is now ready (but we want to ignore it)
        def.resolve();
        await testUtils.nextTick();
        assert.containsOnce(target, ".o_kanban_view", "there should be a kanban view in dom");
        assert.containsNone(target, ".o_list_view", "there should not be a list view in dom");
    });

    QUnit.test("when an server action takes too much time...", async function (assert) {
        assert.expect(1);
        const def = testUtils.makeTestPromise();
        const mockRPC = async function (route, args) {
            if (route === "/web/action/run") {
                await def;
                return 1;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        doAction(webClient, 2);
        doAction(webClient, 4);
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item.active").text(),
            "Partners Action 4",
            "action 4 should be loaded"
        );
    });

    QUnit.test("clicking quickly on breadcrumbs...", async function (assert) {
        assert.expect(1);
        let def;
        const mockRPC = async function (route, args) {
            if (args && args.method === "read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // create a situation with 3 breadcrumbs: kanban/form/list
        await doAction(webClient, 4);
        await testUtils.dom.click($(target).find(".o_kanban_record:first"));
        await legacyExtraNextTick();
        await doAction(webClient, 8);
        await legacyExtraNextTick();
        // now, the next read operations will be promise (this is the read
        // operation for the form view reload)
        def = testUtils.makeTestPromise();
        // click on the breadcrumbs for the form view, then on the kanban view
        // before the form view is fully reloaded
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb-item:eq(1)"));
        await legacyExtraNextTick();
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb-item:eq(0)"));
        await legacyExtraNextTick();
        // resolve the form view read
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item.active").text(),
            "Partners Action 4",
            "action 4 should be loaded and visible"
        );
    });

    QUnit.skip(
        "execute a new action while loading a lazy-loaded controller",
        async function (assert) {
            assert.expect(16);
            let def;
            const mockRPC = async function (route, args) {
                assert.step((args && args.method) || route);
                if (route === "/web/dataset/search_read" && args && args.model === "partner") {
                    await def;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            webClient.env.bus.trigger("test:hashchange", {
                action: 4,
                id: 2,
                view_type: "form",
            });
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_form_view", "should display the form view of action 4");
            // click to go back to Kanban (this request is blocked)
            def = testUtils.makeTestPromise();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a"));
            await legacyExtraNextTick();
            assert.containsOnce(
                target,
                ".o_form_view",
                "should still display the form view of action 4"
            );
            // execute another action meanwhile (don't block this request)
            await doAction(webClient, 8, { clearBreadcrumbs: true });
            assert.containsOnce(target, ".o_list_view", "should display action 8");
            assert.containsNone(target, ".o_form_view", "should no longer display the form view");
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "get_views",
                "read",
                "/web/dataset/search_read",
                "/web/action/load",
                "get_views",
                "/web/dataset/search_read",
            ]);
            // unblock the switch to Kanban in action 4
            def.resolve();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_list_view", "should still display action 8");
            assert.containsNone(
                target,
                ".o_kanban_view",
                "should not display the kanban view of action 4"
            );
            assert.verifySteps([]);
        }
    );

    QUnit.skip("execute a new action while handling a call_button", async function (assert) {
        assert.expect(17);
        const def = testUtils.makeTestPromise();
        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
            if (route === "/web/dataset/call_button") {
                await def;
                return serverData.actions[1];
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute action 3 and open a record in form view
        await doAction(webClient, 3);
        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:first"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view", "should display the form view of action 3");
        // click on 'Call method' button (this request is blocked)
        await testUtils.dom.click($(target).find(".o_form_view button:contains(Call method)"));
        assert.containsOnce(
            target,
            ".o_form_view",
            "should still display the form view of action 3"
        );
        // execute another action
        await doAction(webClient, 8, { clearBreadcrumbs: true });
        assert.containsOnce(target, ".o_list_view", "should display the list view of action 8");
        assert.containsNone(target, ".o_form_view", "should no longer display the form view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "read",
            "object",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
        ]);
        // unblock the call_button request
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(
            target,
            ".o_list_view",
            "should still display the list view of action 8"
        );
        assert.containsNone(target, ".o_kanban_view", "should not display action 1");
        assert.verifySteps([]);
    });

    QUnit.skip(
        "execute a new action while switching to another controller",
        async function (assert) {
            assert.expect(16);
            // This test's bottom line is that a doAction always has priority
            // over a switch controller (clicking on a record row to go to form view).
            // In general, the last actionManager's operation has priority because we want
            // to allow the user to make mistakes, or to rapidly reconsider her next action.
            // Here we assert that the actionManager's RPC are in order, but a 'read' operation
            // is expected, with the current implementation, to take place when switching to the form view.
            // Ultimately the form view's 'read' is superfluous, but can happen at any point of the flow,
            // except at the very end, which should always be the final action's list's 'search_read'.
            let def;
            const mockRPC = async function (route, args) {
                assert.step((args && args.method) || route);
                if (args && args.method === "read") {
                    await def;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view", "should display the list view of action 3");
            // switch to the form view (this request is blocked)
            def = testUtils.makeTestPromise();
            testUtils.dom.click($(target).find(".o_list_view .o_data_row:first"));
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(
                target,
                ".o_list_view",
                "should still display the list view of action 3"
            );
            // execute another action meanwhile (don't block this request)
            await doAction(webClient, 4, { clearBreadcrumbs: true });
            assert.containsOnce(
                target,
                ".o_kanban_view",
                "should display the kanban view of action 8"
            );
            assert.containsNone(target, ".o_list_view", "should no longer display the list view");
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "get_views",
                "/web/dataset/search_read",
                "read",
                "/web/action/load",
                "get_views",
                "/web/dataset/search_read",
            ]);
            // unblock the switch to the form view in action 3
            def.resolve();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(
                target,
                ".o_kanban_view",
                "should still display the kanban view of action 8"
            );
            assert.containsNone(
                target,
                ".o_form_view",
                "should not display the form view of action 3"
            );
            assert.verifySteps([]);
        }
    );

    QUnit.skip("execute a new action while loading views", async function (assert) {
        assert.expect(11);
        const def = testUtils.makeTestPromise();
        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
            if (args && args.method === "get_views") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute a first action (its 'get_views' RPC is blocked)
        doAction(webClient, 3);
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "should not display the list view of action 3");
        // execute another action meanwhile (and unlock the RPC)
        doAction(webClient, 4);
        await testUtils.nextTick();
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view", "should display the kanban view of action 4");
        assert.containsNone(target, ".o_list_view", "should not display the list view of action 3");
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("execute a new action while loading data of default view", async function (assert) {
        assert.expect(12);
        const def = testUtils.makeTestPromise();
        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
            if (route === "/web/dataset/search_read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute a first action (its 'search_read' RPC is blocked)
        doAction(webClient, 3);
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "should not display the list view of action 3");
        // execute another action meanwhile (and unlock the RPC)
        doAction(webClient, 4);
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view", "should display the kanban view of action 4");
        assert.containsNone(target, ".o_list_view", "should not display the list view of action 3");
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("open a record while reloading the list view", async function (assert) {
        assert.expect(12);
        let def;
        const mockRPC = async function (route, args) {
            if (route === "/web/dataset/search_read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_list_view .o_data_row", 5);
        assert.containsOnce(target, ".o_control_panel .o_list_buttons");
        // reload (the search_read RPC will be blocked)
        def = testUtils.makeTestPromise();
        await switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsN(target, ".o_list_view .o_data_row", 5);
        assert.containsOnce(target, ".o_control_panel .o_list_buttons");
        // open a record in form view
        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:first"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsNone(target, ".o_control_panel .o_list_buttons");
        assert.containsOnce(target, ".o_control_panel .o_form_buttons_view");
        // unblock the search_read RPC
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsNone(target, ".o_list_view");
        assert.containsNone(target, ".o_control_panel .o_list_buttons");
        assert.containsOnce(target, ".o_control_panel .o_form_buttons_view");
    });

    QUnit.test(
        "properly drop client actions after new action is initiated",
        async function (assert) {
            assert.expect(3);
            const slowWillStartDef = testUtils.makeTestPromise();
            class ClientAction extends Component {
                setup() {
                    owl.onWillStart(() => slowWillStartDef);
                }
            }
            ClientAction.template = xml`<div class="client_action">ClientAction</div>`;
            actionRegistry.add("slowAction", ClientAction);
            const webClient = await createWebClient({ serverData });
            doAction(webClient, "slowAction");
            await nextTick();
            await legacyExtraNextTick();
            assert.containsNone(target, ".client_action", "client action isn't ready yet");
            doAction(webClient, 4);
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_kanban_view", "should have loaded a kanban view");
            slowWillStartDef.resolve();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_kanban_view", "should still display the kanban view");
        }
    );

    QUnit.skipWOWL("restoring a controller when doing an action -- load_action slow", async function (assert) {
        assert.expect(14);
        let def;
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/action/load") {
                return Promise.resolve(def);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        def = makeDeferred();
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view", "should still contain the form view");
        await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
        def.resolve();
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(target, ".o_form_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "read",
            "/web/action/load",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skipWOWL("switching when doing an action -- load_action slow", async function (assert) {
        assert.expect(12);
        let def;
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/action/load") {
                return Promise.resolve(def);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        def = makeDeferred();
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still contain the list view");
        await switchView(target, "kanban");
        def.resolve();
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(target, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "/web/action/load",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("switching when doing an action -- get_views slow", async function (assert) {
        assert.expect(13);
        let def;
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (args && args.method === "get_views") {
                return Promise.resolve(def);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        def = testUtils.makeTestPromise();
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still contain the list view");
        await switchView(target, "kanban");
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(target, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("switching when doing an action -- search_read slow", async function (assert) {
        assert.expect(13);
        const def = testUtils.makeTestPromise();
        const defs = [null, def, null];
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/dataset/search_read") {
                await Promise.resolve(defs.shift());
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        await switchView(target, "kanban");
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(target, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "/web/action/load",
            "get_views",
            "/web/dataset/search_read",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skip("click multiple times to open a record", async function (assert) {
        assert.expect(5);

        const def = testUtils.makeTestPromise();
        const defs = [null, def];
        const mockRPC = async (route, args) => {
            if (args.method === "read") {
                await Promise.resolve(defs.shift());
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");

        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_row"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");

        await testUtils.dom.click(target.querySelector(".o_back_button"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_list_view");

        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_row"));
        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_row"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view");

        def.resolve();
        await nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
    });

    QUnit.test("local state, global state, and race conditions", async function (assert) {
        serverData.views = {
            "partner,false,toy": `<toy/>`,
            "partner,false,list": `<list><field name="foo"/></list>`,
            "partner,false,search": `
                <search>
                    <filter name="foo" string="Foo" domain="[]"/>
                </search>
            `,
        };

        let def = Promise.resolve();

        let id = 1;
        class ToyController extends Component {
            setup() {
                this.id = id++;
                assert.step(JSON.stringify(this.props.state || "no state"));
                useSetupView({
                    getLocalState: () => {
                        return { fromId: this.id };
                    },
                });
                owl.onWillStart(() => def);
            }
        }
        ToyController.template = xml`
            <div class="o_toy_view">
                <ControlPanel />
            </div>`;
        ToyController.components = { ControlPanel };

        registry.category("views").add("toy", {
            type: "toy",
            display_name: "Toy",
            icon: "fab fa-android",
            multiRecord: true,
            searchMenuTypes: ["filter"],
            Controller: ToyController,
        });

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            // list (or something else) must be added to have the view switcher displayed
            views: [
                [false, "toy"],
                [false, "list"],
            ],
        });

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Foo");
        assert.ok(isItemSelected(target, "Foo"));

        // reload twice by clicking on toy view switcher
        def = makeDeferred();
        await click(target.querySelector(".o_control_panel .o_switch_view.o_toy"));
        await click(target.querySelector(".o_control_panel .o_switch_view.o_toy"));

        def.resolve();
        await nextTick();

        await toggleFilterMenu(target);
        assert.ok(isItemSelected(target, "Foo"));
        // this test is not able to detect that getGlobalState is put on the right place:
        // currentController.action.globalState contains in any case the search state
        // of the first instantiated toy view.

        assert.verifySteps([
            `"no state"`, // setup first view instantiated
            `{"fromId":1}`, // setup second view instantiated
            `{"fromId":1}`, // setup third view instantiated
        ]);
    });
});
