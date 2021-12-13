/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useSetupView } from "@web/views/helpers/view_hook";
import { click, legacyExtraNextTick, makeDeferred, nextTick } from "@web/../tests/helpers/utils";
import { isItemSelected, toggleFilterMenu, toggleMenuItem } from "@web/../tests/search/helpers";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
    loadState,
} from "@web/../tests/webclient/helpers";

const { Component, tags } = owl;
const actionRegistry = registry.category("actions");

let serverData;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
    });

    QUnit.module("Concurrency management");

    QUnit.test("drop previous actions if possible", async function (assert) {
        assert.expect(7);
        const def = makeDeferred();
        const mockRPC = async function (route) {
            assert.step(route);
            if (route === "/web/action/load") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        doAction(webClient, 4);
        doAction(webClient, 8);
        def.resolve();
        await nextTick();
        // action 4 loads a kanban view first, 6 loads a list view. We want a list
        assert.containsOnce(webClient, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/action/load",
            "/web/dataset/call_kw/pony/load_views",
            "/web/dataset/call_kw/pony/web_search_read",
        ]);
    });

    QUnit.test("handle switching view and switching back on slow network", async function (assert) {
        assert.expect(9);
        const def = makeDeferred();
        const defs = [Promise.resolve(), def, Promise.resolve()];
        const mockRPC = async function (route, { method }) {
            assert.step(route);
            if (method === "web_search_read") {
                await defs.shift();
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 4);
        // kanban view is loaded, switch to list view
        await click(webClient.el.querySelector(".o_switch_view.o_list"));
        // here, list view is not ready yet, because def is not resolved
        // switch back to kanban view
        await click(webClient.el.querySelector(".o_switch_view.o_kanban"));
        // here, we want the kanban view to reload itself, regardless of list view
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/load_views",
            "/web/dataset/call_kw/partner/web_search_read",
            "/web/dataset/call_kw/partner/web_search_read",
            "/web/dataset/call_kw/partner/web_search_read",
        ]);
        // we resolve def => list view is now ready (but we want to ignore it)
        def.resolve();
        await nextTick();
        assert.containsOnce(webClient, ".o_kanban_view", "there should be a kanban view in dom");
        assert.containsNone(webClient, ".o_list_view", "there should not be a list view in dom");
    });

    QUnit.test("when an server action takes too much time...", async function (assert) {
        assert.expect(1);
        const def = makeDeferred();
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
        await nextTick();
        await legacyExtraNextTick();
        assert.strictEqual(
            $(webClient.el).find(".o_control_panel .breadcrumb-item.active").text(),
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
        await click(webClient.el.querySelector(".o_kanban_record"));
        await doAction(webClient, 8);
        // now, the next read operations will be promise (this is the read
        // operation for the form view reload)
        def = makeDeferred();
        // click on the breadcrumbs for the form view, then on the kanban view
        // before the form view is fully reloaded
        await click(webClient.el.querySelectorAll(".o_control_panel .breadcrumb-item")[1]);
        await click(webClient.el.querySelector(".o_control_panel .breadcrumb-item"));
        // resolve the form view read
        def.resolve();
        await nextTick();
        assert.strictEqual(
            $(webClient.el).find(".o_control_panel .breadcrumb-item.active").text(),
            "Partners Action 4",
            "action 4 should be loaded and visible"
        );
    });

    QUnit.test(
        "execute a new action while loading a lazy-loaded controller",
        async function (assert) {
            assert.expect(16);
            let def;
            const mockRPC = async function (route, { method, model }) {
                assert.step(method || route);
                if (method === "web_search_read" && model === "partner") {
                    await def;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await loadState(webClient, {
                action: 4,
                id: 2,
                view_type: "form",
            });
            assert.containsOnce(
                webClient.el,
                ".o_form_view",
                "should display the form view of action 4"
            );
            // click to go back to Kanban (this request is blocked)
            def = makeDeferred();
            await click(webClient.el.querySelector(".o_control_panel .breadcrumb a"));
            assert.containsOnce(
                webClient.el,
                ".o_form_view",
                "should still display the form view of action 4"
            );
            // execute another action meanwhile (don't block this request)
            await doAction(webClient, 8, { clearBreadcrumbs: true });
            assert.containsOnce(webClient, ".o_list_view", "should display action 8");
            assert.containsNone(
                webClient,
                ".o_form_view",
                "should no longer display the form view"
            );
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "load_views",
                "read",
                "web_search_read",
                "/web/action/load",
                "load_views",
                "web_search_read",
            ]);
            // unblock the switch to Kanban in action 4
            def.resolve();
            await nextTick();
            assert.containsOnce(webClient, ".o_list_view", "should still display action 8");
            assert.containsNone(
                webClient.el,
                ".o_kanban_view",
                "should not display the kanban view of action 4"
            );
            assert.verifySteps([]);
        }
    );

    QUnit.test("execute a new action while handling a call_button", async function (assert) {
        assert.expect(17);
        const def = makeDeferred();
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
        await click(webClient.el.querySelector(".o_list_view .o_data_row"));
        assert.containsOnce(webClient, ".o_form_view", "should display the form view of action 3");
        // click on 'Call method' button (this request is blocked)
        await click(webClient.el.querySelector('.o_form_view button[name="object"]'));
        assert.containsOnce(
            webClient.el,
            ".o_form_view",
            "should still display the form view of action 3"
        );
        // execute another action
        await doAction(webClient, 8, { clearBreadcrumbs: true });
        assert.containsOnce(webClient, ".o_list_view", "should display the list view of action 8");
        assert.containsNone(webClient, ".o_form_view", "should no longer display the form view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "load_views",
            "web_search_read",
            "read",
            "object",
            "/web/action/load",
            "load_views",
            "web_search_read",
        ]);
        // unblock the call_button request
        def.resolve();
        await nextTick();
        assert.containsOnce(
            webClient.el,
            ".o_list_view",
            "should still display the list view of action 8"
        );
        assert.containsNone(webClient, ".o_kanban_view", "should not display action 1");
        assert.verifySteps([]);
    });

    QUnit.test(
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
            assert.containsOnce(
                webClient,
                ".o_list_view",
                "should display the list view of action 3"
            );
            // switch to the form view (this request is blocked)
            def = makeDeferred();
            await click(webClient.el.querySelector(".o_list_view .o_data_row"));
            assert.containsOnce(
                webClient.el,
                ".o_list_view",
                "should still display the list view of action 3"
            );
            // execute another action meanwhile (don't block this request)
            await doAction(webClient, 4, { clearBreadcrumbs: true });
            assert.containsOnce(
                webClient.el,
                ".o_kanban_view",
                "should display the kanban view of action 8"
            );
            assert.containsNone(
                webClient,
                ".o_list_view",
                "should no longer display the list view"
            );
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "load_views",
                "web_search_read",
                "read",
                "/web/action/load",
                "load_views",
                "web_search_read",
            ]);
            // unblock the switch to the form view in action 3
            def.resolve();
            await nextTick();
            assert.containsOnce(
                webClient.el,
                ".o_kanban_view",
                "should still display the kanban view of action 8"
            );
            assert.containsNone(
                webClient.el,
                ".o_form_view",
                "should not display the form view of action 3"
            );
            assert.verifySteps([]);
        }
    );

    QUnit.test("execute a new action while loading views", async function (assert) {
        assert.expect(11);
        const def = makeDeferred();
        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
            if (args && args.method === "load_views") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute a first action (its 'load_views' RPC is blocked)
        doAction(webClient, 3);
        await nextTick();
        assert.containsNone(
            webClient.el,
            ".o_list_view",
            "should not display the list view of action 3"
        );
        // execute another action meanwhile (and unlock the RPC)
        doAction(webClient, 4);
        await nextTick();
        def.resolve();
        await nextTick();
        assert.containsOnce(
            webClient.el,
            ".o_kanban_view",
            "should display the kanban view of action 4"
        );
        assert.containsNone(
            webClient.el,
            ".o_list_view",
            "should not display the list view of action 3"
        );
        assert.containsOnce(
            webClient.el,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "load_views",
            "/web/action/load",
            "load_views",
            "web_search_read",
        ]);
    });

    QUnit.test("execute a new action while loading data of default view", async function (assert) {
        assert.expect(12);
        const def = makeDeferred();
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
            if (method === "web_search_read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute a first action (its 'search_read' RPC is blocked)
        doAction(webClient, 3);
        await nextTick();
        assert.containsNone(
            webClient.el,
            ".o_list_view",
            "should not display the list view of action 3"
        );
        // execute another action meanwhile (and unlock the RPC)
        doAction(webClient, 4);
        def.resolve();
        await nextTick();
        assert.containsOnce(
            webClient.el,
            ".o_kanban_view",
            "should display the kanban view of action 4"
        );
        assert.containsNone(
            webClient.el,
            ".o_list_view",
            "should not display the list view of action 3"
        );
        assert.containsOnce(
            webClient.el,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "load_views",
            "web_search_read",
            "/web/action/load",
            "load_views",
            "web_search_read",
        ]);
    });

    QUnit.test("open a record while reloading the list view", async function (assert) {
        assert.expect(12);
        let def;
        const mockRPC = async function (route) {
            if (route === "/web/dataset/search_read") {
                await def;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(webClient, ".o_list_view");
        assert.containsN(webClient, ".o_list_view .o_data_row", 5);
        assert.containsOnce(webClient, ".o_control_panel .o_list_buttons");
        // reload (the search_read RPC will be blocked)
        def = makeDeferred();
        await click(webClient.el.querySelector(".o_switch_view.o_list"));
        assert.containsN(webClient, ".o_list_view .o_data_row", 5);
        assert.containsOnce(webClient, ".o_control_panel .o_list_buttons");
        // open a record in form view
        await click(webClient.el.querySelector(".o_list_view .o_data_row"));
        assert.containsOnce(webClient, ".o_form_view");
        assert.containsNone(webClient, ".o_control_panel .o_list_buttons");
        assert.containsOnce(webClient, ".o_control_panel .o_form_buttons_view");
        // unblock the search_read RPC
        def.resolve();
        await nextTick();
        assert.containsOnce(webClient, ".o_form_view");
        assert.containsNone(webClient, ".o_list_view");
        assert.containsNone(webClient, ".o_control_panel .o_list_buttons");
        assert.containsOnce(webClient, ".o_control_panel .o_form_buttons_view");
    });

    QUnit.test(
        "properly drop client actions after new action is initiated",
        async function (assert) {
            assert.expect(3);
            const slowWillStartDef = makeDeferred();
            class ClientAction extends Component {
                willStart() {
                    return slowWillStartDef;
                }
            }
            ClientAction.template = tags.xml`<div class="client_action">ClientAction</div>`;
            actionRegistry.add("slowAction", ClientAction);
            const webClient = await createWebClient({ serverData });
            doAction(webClient, "slowAction");
            await nextTick();
            await legacyExtraNextTick();
            assert.containsNone(webClient, ".client_action", "client action isn't ready yet");
            doAction(webClient, 4);
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(webClient, ".o_kanban_view", "should have loaded a kanban view");
            slowWillStartDef.resolve();
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(
                webClient,
                ".o_kanban_view",
                "should still display the kanban view"
            );
        }
    );

    QUnit.test("switching when doing an action -- load_views slow", async function (assert) {
        assert.expect(13);
        let def;
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (args && args.method === "load_views") {
                return Promise.resolve(def);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(webClient, ".o_list_view");
        def = makeDeferred();
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await nextTick();
        assert.containsOnce(webClient, ".o_list_view", "should still contain the list view");
        await click(webClient.el.querySelector(".o_switch_view.o_kanban"));
        def.resolve();
        await nextTick();
        assert.containsOnce(webClient, ".o_kanban_view");
        assert.strictEqual(
            webClient.el.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(webClient, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "load_views",
            "web_search_read",
            "/web/action/load",
            "load_views",
            "web_search_read",
        ]);
    });

    QUnit.test("switching when doing an action -- search_read slow", async function (assert) {
        assert.expect(13);
        const def = makeDeferred();
        const defs = [null, def, null];
        const mockRPC = async (route, { method }) => {
            assert.step(method || route);
            if (method === "web_search_read") {
                await Promise.resolve(defs.shift());
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(webClient, ".o_list_view");
        doAction(webClient, 4, { clearBreadcrumbs: true });
        await nextTick();
        await click(webClient.el.querySelector(".o_switch_view.o_kanban"));
        def.resolve();
        await nextTick();
        assert.containsOnce(webClient, ".o_kanban_view");
        assert.strictEqual(
            webClient.el.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "Partners"
        );
        assert.containsNone(webClient, ".o_list_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "load_views",
            "web_search_read",
            "/web/action/load",
            "load_views",
            "web_search_read",
            "web_search_read",
        ]);
    });

    QUnit.skip("click multiple times to open a record", async function (assert) {
        assert.expect(5);

        const def = makeDeferred();
        const defs = [null, def];
        const mockRPC = async (route, args) => {
            if (args.method === "read") {
                await Promise.resolve(defs.shift());
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(webClient, ".o_list_view");

        await click(webClient.el.querySelector(".o_list_view .o_data_row"));
        assert.containsOnce(webClient, ".o_form_view");

        await click(webClient.el.querySelector(".o_back_button"));
        assert.containsOnce(webClient, ".o_list_view");

        await click(webClient.el.querySelector(".o_list_view .o_data_row"));
        await click(webClient.el.querySelector(".o_list_view .o_data_row"));
        assert.containsOnce(webClient, ".o_list_view");

        def.resolve();
        await nextTick();
        assert.containsOnce(webClient, ".o_form_view");
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
        class ToyView extends Component {
            setup() {
                this.id = id++;
                assert.step(JSON.stringify(this.props.state || "no state"));
                useSetupView({
                    getLocalState: () => {
                        return { fromId: this.id };
                    },
                });
            }
            async willStart() {
                await def;
            }
        }
        ToyView.components = { ControlPanel };
        ToyView.display_name = "Toy";
        ToyView.icon = "fab fa-android";
        ToyView.multiRecord = true;
        ToyView.searchMenuTypes = ["filter"];
        ToyView.template = owl.tags.xml`
            <div class="o_toy_view">
                <ControlPanel />
            </div>
        `;
        ToyView.type = "toy";
        registry.category("views").add("toy", ToyView);

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

        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, "Foo");
        assert.ok(isItemSelected(webClient, "Foo"));

        // reload twice by clicking on toy view switcher
        def = makeDeferred();
        await click(webClient.el.querySelector(".o_control_panel .o_switch_view.o_toy"));
        await click(webClient.el.querySelector(".o_control_panel .o_switch_view.o_toy"));

        def.resolve();
        await nextTick();

        await toggleFilterMenu(webClient);
        assert.ok(isItemSelected(webClient, "Foo"));
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
