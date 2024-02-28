/** @odoo-module **/

import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import ListController from "web.ListController";
import FormView from "web.FormView";
import ListView from "web.ListView";
import {
    click,
    destroy,
    getFixture,
    makeDeferred,
    legacyExtraNextTick,
    patchWithCleanup,
    triggerEvents,
} from "../../helpers/utils";
import KanbanView from "web.KanbanView";
import { registerCleanup } from "../../helpers/cleanup";
import { makeTestEnv } from "../../helpers/mock_env";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import makeTestEnvironment from "web.test_env";

import { ClientActionAdapter, ViewAdapter } from "@web/legacy/action_adapters";
import { makeLegacyCrashManagerService } from "@web/legacy/utils";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import * as cpHelpers from "@web/../tests/search/helpers";

import AbstractView from "web.AbstractView";
import ControlPanel from "web.ControlPanel";
import core from "web.core";
import AbstractAction from "web.AbstractAction";
import Widget from "web.Widget";
import SystrayMenu from "web.SystrayMenu";
import legacyViewRegistry from "web.view_registry";

let serverData;
let target;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        registry.category("views").remove("form"); // remove new form from registry
        registry.category("views").remove("kanban"); // remove new kanban from registry
        registry.category("views").remove("list"); // remove new list from registry
        legacyViewRegistry.add("form", FormView); // add legacy form -> will be wrapped and added to new registry
        legacyViewRegistry.add("kanban", KanbanView); // add legacy kanban -> will be wrapped and added to new registry
        legacyViewRegistry.add("list", ListView); // add legacy list -> will be wrapped and added to new registry

        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Legacy tests (to eventually drop)");

    QUnit.test("display warning as notification", async function (assert) {
        // this test can be removed as soon as the legacy layer is dropped
        assert.expect(5);
        let list;
        patchWithCleanup(ListController.prototype, {
            init() {
                this._super(...arguments);
                list = this;
            },
        });

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_legacy_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_list_view");
        assert.containsOnce(document.body, ".o_notification.border-warning");
        assert.strictEqual($(".o_notification_title").text(), "Warning!!!");
        assert.strictEqual($(".o_notification_content").text(), "This is a warning...");
    });

    QUnit.test("display warning as modal", async function (assert) {
        // this test can be removed as soon as the legacy layer is dropped
        assert.expect(5);
        let list;
        patchWithCleanup(ListController.prototype, {
            init() {
                this._super(...arguments);
                list = this;
            },
        });

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_legacy_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...",
            type: "dialog",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_list_view");
        assert.containsOnce(document.body, ".modal");
        assert.strictEqual($(".modal-title").text(), "Warning!!!");
        assert.strictEqual($(".modal-body").text(), "This is a warning...");
    });

    QUnit.test("display multiline warning as modal", async function (assert) {
        assert.expect(5);
        let list;
        patchWithCleanup(ListController.prototype, {
            init() {
                this._super(...arguments);
                list = this;
            },
        });

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_legacy_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...\nabc",
            type: "dialog",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_list_view");
        assert.containsOnce(document.body, ".modal");
        assert.strictEqual($(".modal-title").text(), "Warning!!!");
        assert.strictEqual($(".modal-body")[0].innerText, "This is a warning...\nabc");
    });

    QUnit.test(
        "legacy crash manager is still properly remapped to error service",
        async function (assert) {
            // this test can be removed as soon as the legacy layer is dropped
            assert.expect(2);

            const legacyEnv = makeTestEnvironment();
            registry
                .category("services")
                .add("legacy_crash_manager", makeLegacyCrashManagerService(legacyEnv))
                .add("dialog", {
                    start() {
                        return {
                            add(dialogClass, props) {
                                assert.strictEqual(dialogClass, ErrorDialog);
                                assert.strictEqual(props.traceback, "BOOM");
                            },
                        };
                    },
                });
            await makeTestEnv();
            legacyEnv.services.crash_manager.show_message("BOOM");
        }
    );

    QUnit.test("redraw a controller and open debugManager does not crash", async (assert) => {
        assert.expect(11);

        const LegacyAction = AbstractAction.extend({
            start() {
                const ret = this._super(...arguments);
                const el = document.createElement("div");
                el.classList.add("custom-action");
                this.el.append(el);
                return ret;
            },
        });
        core.action_registry.add("customLegacy", LegacyAction);

        patchWithCleanup(ClientActionAdapter.prototype, {
            setup() {
                useDebugCategory("custom", { widget: this });
                this._super();
            },
        });

        registry
            .category("debug")
            .category("custom")
            .add("item1", ({ widget }) => {
                assert.step("debugItems executed");
                assert.ok(widget);
                return {};
            });
        patchWithCleanup(odoo, { debug: true });

        const mockRPC = (route) => {
            if (route.includes("check_access_rights")) {
                return true;
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, "customLegacy");
        assert.containsOnce(target, ".custom-action");
        assert.verifySteps([]);

        await click(target, ".o_debug_manager button");
        assert.verifySteps(["debugItems executed"]);

        await doAction(webClient, 5); // action in Dialog
        await click(target, ".modal .o_form_button_cancel");
        assert.containsNone(target, ".modal");
        assert.containsOnce(target, ".custom-action");
        assert.verifySteps([]);

        // close debug menu
        await click(target, ".o_debug_manager button");
        // open debug menu
        await click(target, ".o_debug_manager button");
        assert.verifySteps(["debugItems executed"]);
        delete core.action_registry.map.customLegacy;
    });

    QUnit.test("willUnmount is called down the legacy layers", async (assert) => {
        assert.expect(7);

        let mountCount = 0;
        patchWithCleanup(ControlPanel.prototype, {
            setup() {
                this._super();
                owl.onMounted(() => {
                    mountCount = mountCount + 1;
                    this.__uniqueId = mountCount;
                    assert.step(`mounted ${this.__uniqueId}`);
                });
                owl.onWillUnmount(() => {
                    assert.step(`willUnmount ${this.__uniqueId}`);
                });
            },
        });

        const LegacyAction = AbstractAction.extend({
            hasControlPanel: true,
            start() {
                const ret = this._super(...arguments);
                const el = document.createElement("div");
                el.classList.add("custom-action");
                this.el.append(el);
                return ret;
            },
        });
        core.action_registry.add("customLegacy", LegacyAction);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        await doAction(webClient, "customLegacy");
        await click(target.querySelectorAll(".breadcrumb-item")[0]);
        await legacyExtraNextTick();

        destroy(webClient);

        assert.verifySteps([
            "mounted 1",
            "willUnmount 1",
            "mounted 2",
            "willUnmount 2",
            "mounted 3",
            "willUnmount 3",
        ]);

        delete core.action_registry.map.customLegacy;
    });

    QUnit.test("Checks the availability of all views in the action", async (assert) => {
        assert.expect(2);
        patchWithCleanup(ListView.prototype, {
            init(viewInfo, params) {
                const action = params.action;
                const views = action.views.map((view) => [view.viewID, view.type]);
                assert.deepEqual(views, [
                    [1, "list"],
                    [2, "kanban"],
                    [3, "form"],
                ]);
                assert.deepEqual(action._views, [
                    [1, "list"],
                    [2, "kanban"],
                    [3, "form"],
                    [false, "search"],
                ]);
                this._super(...arguments);
            },
        });
        const models = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char", searchable: true },
                    foo: {
                        string: "Foo",
                        type: "char",
                        default: "My little Foo Value",
                        searchable: true,
                    },
                    bar: { string: "Bar", type: "boolean" },
                    int_field: { string: "Integer field", type: "integer", group_operator: "sum" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "first record",
                        foo: "yop",
                        int_field: 3,
                    },
                    {
                        id: 2,
                        display_name: "second record",
                        foo: "lalala",
                        int_field: 5,
                    },
                    {
                        id: 4,
                        display_name: "aaa",
                        foo: "abc",
                        int_field: 2,
                    },
                ],
            },
        };
        const views = {
            "partner,1,list": '<list><field name="foo"/></list>',
            "partner,2,kanban": "<kanban></kanban>",
            "partner,3,form": `<form></form>`,
            "partner,false,search": "<search></search>",
        };
        const serverData = { models, views };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [1, "list"],
                [2, "kanban"],
                [3, "form"],
            ],
        });
    });

    QUnit.test("client actions may take and push their params", async function (assert) {
        assert.expect(2);

        const ClientAction = AbstractAction.extend({
            init(parent, action) {
                this._super(...arguments);
                assert.deepEqual(action.params, {
                    active_id: 99,
                    take: "five",
                    active_ids: "1,2",
                    list: [9, 10],
                });
            },
        });
        core.action_registry.add("clientAction", ClientAction);
        registerCleanup(() => delete core.action_registry.map.clientAction);
        const webClient = await createWebClient({});

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "clientAction",
            params: {
                active_id: 99,
                take: "five",
                active_ids: "1,2",
                list: [9, 10],
            },
        });

        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "clientAction",
            active_id: 99,
            take: "five",
            active_ids: "1,2",
        });
    });

    QUnit.test("client actions honour do_push_state", async function (assert) {
        assert.expect(2);

        const ClientAction = AbstractAction.extend({
            init(parent) {
                this._super(...arguments);
                this.parent = parent;
                this.parent.do_push_state({ pinball: "wizard" });
            },

            async start() {
                await this._super(...arguments);
                const btn = document.createElement("button");
                btn.classList.add("tommy");
                btn.addEventListener("click", () => {
                    this.parent.do_push_state({ gipsy: "the acid queen" });
                });
                this.el.append(btn);
            },

            getState() {
                return {
                    doctor: "quackson",
                };
            },
        });
        core.action_registry.add("clientAction", ClientAction);
        registerCleanup(() => delete core.action_registry.map.clientAction);
        const webClient = await createWebClient({});

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "clientAction",
        });

        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "clientAction",
            pinball: "wizard",
            doctor: "quackson",
        });

        await click(target, ".tommy");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "clientAction",
            pinball: "wizard",
            gipsy: "the acid queen",
            doctor: "quackson",
        });
    });

    QUnit.test("Systray item triggers do action on legacy service provider", async (assert) => {
        assert.expect(3);
        function createMockActionService(assert) {
            return {
                dependencies: [],
                start() {
                    return {
                        doAction(params) {
                            assert.step("do action");
                            assert.strictEqual(params, 128, "The doAction parameters are invalid.");
                        },
                        loadState() {},
                    };
                },
            };
        }
        registry.category("services").add("action", createMockActionService(assert));
        const FakeSystrayItemWidget = Widget.extend({
            on_attach_callback() {
                this.do_action(128);
            },
        });
        SystrayMenu.Items.push(FakeSystrayItemWidget);
        await createWebClient({ serverData });
        assert.verifySteps(["do action"]);
        delete SystrayMenu.Items.FakeSystrayItemWidget;
    });

    QUnit.test("usercontext always added to legacy actions", async (assert) => {
        assert.expect(8);
        core.action_registry.add("testClientAction", AbstractAction);
        registerCleanup(() => delete core.action_registry.map.testClientAction);
        patchWithCleanup(ClientActionAdapter.prototype, {
            setup() {
                assert.step("ClientActionAdapter");
                const action = { ...this.props.widgetArgs[0] };
                const originalAction = JSON.parse(action._originalAction);
                assert.deepEqual(originalAction.context, undefined);
                assert.deepEqual(action.context, this.env.services.user.context);
                this._super();
            },
        });
        patchWithCleanup(ViewAdapter.prototype, {
            setup() {
                assert.step("ViewAdapter");
                const action = { ...this.props.viewParams.action };
                const originalAction = JSON.parse(action._originalAction);
                assert.deepEqual(originalAction.context, undefined);
                assert.deepEqual(action.context, this.env.services.user.context);
                this._super();
            },
        });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "testClientAction");
        assert.verifySteps(["ClientActionAdapter"]);
        await doAction(webClient, 1);
        assert.verifySteps(["ViewAdapter"]);
    });

    QUnit.test("correctly transports legacy Props for doAction", async (assert) => {
        assert.expect(4);

        let ID = 0;
        const MyAction = AbstractAction.extend({
            init() {
                this._super(...arguments);
                this.ID = ID++;
                assert.step(`id: ${this.ID} props: ${JSON.stringify(arguments[2])}`);
            },
            async start() {
                const res = await this._super(...arguments);
                const link = document.createElement("a");
                link.innerText = "some link";
                link.setAttribute("id", `client_${this.ID}`);
                link.addEventListener("click", () => {
                    this.do_action("testClientAction", {
                        clear_breadcrumbs: true,
                        props: { chain: "never break" },
                    });
                });

                this.el.appendChild(link);
                return res;
            },
        });
        core.action_registry.add("testClientAction", MyAction);
        registerCleanup(() => delete core.action_registry.map.testClientAction);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "testClientAction");
        assert.verifySteps(['id: 0 props: {"className":"o_action","breadcrumbs":[]}']);

        await click(document.getElementById("client_0"));
        assert.verifySteps([
            'id: 1 props: {"chain":"never break","className":"o_action","breadcrumbs":[]}',
        ]);
    });

    QUnit.test("bootstrap tooltip in dialog action auto destroy", async (assert) => {
        assert.expect(2);

        const mockRPC = (route) => {
            if (route === "/web/dataset/call_button") {
                return false;
            }
        };

        serverData.views["partner,3,form"] = /*xml*/ `
            <form>
                <field name="display_name" />
                <footer>
                    <button name="echoes" type="object" string="Echoes" help="echoes"/>
                </footer>
            </form>
        `;
        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 25);

        const tooltipProm = makeDeferred();
        $(target).one("shown.bs.tooltip", () => {
            tooltipProm.resolve();
        });

        triggerEvents(target, ".modal footer button", ["mouseover", "focusin"]);
        await tooltipProm;
        // check on webClient dom
        assert.containsOnce(document.body, ".tooltip");
        await doAction(webClient, {
            type: "ir.actions.act_window_close",
        });
        // check on the whole DOM
        assert.containsNone(document.body, ".tooltip");
    });

    QUnit.test("bootstrap tooltip destroyed on click", async (assert) => {
        assert.expect(2);

        const mockRPC = (route) => {
            if (route === "/web/dataset/call_button") {
                return false;
            }
        };

        serverData.views["partner,666,form"] = /*xml*/ `
            <form>
                <header>
                    <button name="echoes" type="object" string="Echoes" help="echoes"/>
                </header>
                <field name="display_name" />
            </form>
        `;
        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 24);

        const tooltipProm = makeDeferred();
        $(target).one("shown.bs.tooltip", () => {
            tooltipProm.resolve();
        });

        triggerEvents(target, ".o_form_statusbar button", ["mouseover", "focusin"]);
        await tooltipProm;
        // check on webClient DOM
        assert.containsOnce(document.body, ".tooltip");
        await click(target, ".o_content");
        // check on the whole DOM
        assert.containsNone(document.body, ".tooltip");
    });

    QUnit.test("breadcrumbs are correct in stacked legacy client actions", async function (assert) {
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            async start() {
                this.$el.addClass("client_action");
                return this._super(...arguments);
            },
            getTitle() {
                return "Blabla";
            },
        });
        core.action_registry.add("clientAction", ClientAction);
        registerCleanup(() => delete core.action_registry.map.clientAction);

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_legacy_list_view");
        assert.strictEqual($(target).find(".breadcrumb-item").text(), "Partners");

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "clientAction",
        });
        assert.containsOnce(target, ".client_action");
        assert.strictEqual($(target).find(".breadcrumb-item").text(), "PartnersBlabla");
    });

    QUnit.test("view with js_class attribute (legacy)", async function (assert) {
        assert.expect(2);
        const TestView = AbstractView.extend({
            viewType: "test_view",
        });
        const TestJsClassView = TestView.extend({
            init() {
                this._super.call(this, ...arguments);
                assert.step("init js class");
            },
        });
        serverData.views["partner,false,test_view"] = `<div js_class="test_jsClass"></div>`;
        serverData.actions[9999] = {
            id: 1,
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "test_view"]],
        };
        legacyViewRegistry.add("test_view", TestView);
        legacyViewRegistry.add("test_jsClass", TestJsClassView);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 9999);
        assert.verifySteps(["init js class"]);
        delete legacyViewRegistry.map.test_view;
        delete legacyViewRegistry.map.test_jsClass;
    });

    QUnit.test(
        "execute action without modal closes bootstrap tooltips anyway",
        async function (assert) {
            assert.expect(12);
            Object.assign(serverData.views, {
                "partner,666,form": `<form>
            <header>
              <button name="object" string="Call method" type="object" help="need somebody"/>
            </header>
            <field name="display_name"/>
          </form>`,
            });
            const mockRPC = async (route) => {
                assert.step(route);
                if (route === "/web/dataset/call_button") {
                    // Some business stuff server side, then return an implicit close action
                    return Promise.resolve(false);
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 24);
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/read",
            ]);
            assert.containsN(target, ".o_form_buttons_view button:not([disabled])", 2);
            const actionButton = target.querySelector("button[name=object]");
            const tooltipProm = new Promise((resolve) => {
                document.body.addEventListener(
                    "shown.bs.tooltip",
                    () => {
                        actionButton.dispatchEvent(new Event("mouseout"));
                        resolve();
                    },
                    {
                        once: true,
                    }
                );
            });
            actionButton.dispatchEvent(new Event("mouseover"));
            await tooltipProm;
            assert.containsOnce(document.body, ".tooltip");
            await click(actionButton);
            await legacyExtraNextTick();
            assert.verifySteps(["/web/dataset/call_button", "/web/dataset/call_kw/partner/read"]);
            assert.containsNone(document.body, ".tooltip"); // body different from webClient in tests !
            assert.containsN(target, ".o_form_buttons_view button:not([disabled])", 2);
        }
    );

    QUnit.test("click multiple times to open a record", async function (assert) {
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

        assert.containsOnce(target, ".o_legacy_list_view");

        await testUtils.dom.click(target.querySelector(".o_legacy_list_view .o_data_row"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_form_view");

        await testUtils.dom.click(target.querySelector(".o_back_button"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_legacy_list_view");

        await testUtils.dom.click(target.querySelector(".o_legacy_list_view .o_data_row"));
        await testUtils.dom.click(target.querySelector(".o_legacy_list_view .o_data_row"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_list_view");

        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_legacy_form_view");
    });

    QUnit.test("correct pager when coming from list (legacy)", async (assert) => {
        assert.expect(4);

        registry.category("views").remove("list");
        legacyViewRegistry.add("list", ListView);
        serverData.views = {
            "partner,false,search": `<search />`,
            "partner,99,list": `<list limit="4"><field name="display_name" /></list>`,
            "partner,100,form": `<form><field name="display_name" /></form>`,
        };

        const wc = await createWebClient({ serverData });
        await doAction(wc, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [99, "list"],
                [100, "form"],
            ],
        });

        assert.deepEqual(cpHelpers.getPagerValue(target), [1, 4]);
        assert.deepEqual(cpHelpers.getPagerLimit(target), 5);

        await click(target, ".o_data_row:nth-child(2) .o_data_cell");
        await legacyExtraNextTick();
        assert.deepEqual(cpHelpers.getPagerValue(target), [2]);
        assert.deepEqual(cpHelpers.getPagerLimit(target), 4);
    });
});
