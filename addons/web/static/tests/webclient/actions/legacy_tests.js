/** @odoo-module **/

import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import ListController from "web.ListController";
import ListView from "web.ListView";
import { click, legacyExtraNextTick, patchWithCleanup } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";
import { makeTestEnv } from "../../helpers/mock_env";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import makeTestEnvironment from "web.test_env";

import { ClientActionAdapter, ViewAdapter } from "@web/legacy/action_adapters";
import { makeLegacyCrashManagerService } from "@web/legacy/utils";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { ErrorDialog } from "@web/core/errors/error_dialogs";

import ControlPanel from "web.ControlPanel";
import core from "web.core";
import AbstractAction from "web.AbstractAction";
import Widget from "web.Widget";
import SystrayMenu from "web.SystrayMenu";

let serverData;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
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
        assert.containsOnce(webClient, ".o_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_list_view");
        assert.containsOnce(document.body, ".o_notification.bg-warning");
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
        assert.containsOnce(webClient, ".o_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...",
            type: "dialog",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_list_view");
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
        assert.containsOnce(webClient, ".o_list_view");
        list.trigger_up("warning", {
            title: "Warning!!!",
            message: "This is a warning...\nabc",
            type: "dialog",
        });
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_list_view");
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
        assert.containsOnce(webClient, ".custom-action");
        assert.verifySteps([]);

        await click(webClient.el, ".o_debug_manager button");
        assert.verifySteps(["debugItems executed"]);

        await doAction(webClient, 5); // action in Dialog
        await click(webClient.el, ".modal .o_form_button_cancel");
        assert.containsNone(webClient, ".modal");
        assert.containsOnce(webClient, ".custom-action");
        assert.verifySteps([]);

        // close debug menu
        await click(webClient.el, ".o_debug_manager button");
        // open debug menu
        await click(webClient.el, ".o_debug_manager button");
        assert.verifySteps(["debugItems executed"]);
        delete core.action_registry.map.customLegacy;
    });

    QUnit.test("willUnmount is called down the legacy layers", async (assert) => {
        assert.expect(7);

        let mountCount = 0;
        patchWithCleanup(ControlPanel.prototype, {
            mounted() {
                mountCount = mountCount + 1;
                this.__uniqueId = mountCount;
                assert.step(`mounted ${this.__uniqueId}`);
                this._super(...arguments);
            },
            willUnmount() {
                assert.step(`willUnmount ${this.__uniqueId}`);
                this._super(...arguments);
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
        await click(webClient.el.querySelectorAll(".breadcrumb-item")[0]);
        await legacyExtraNextTick();

        webClient.destroy();

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

        const webClient = await createWebClient({
            serverData,
        });

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

        await click(webClient.el, ".tommy");
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
        assert.verifySteps(['id: 0 props: {"breadcrumbs":[]}']);

        await click(document.getElementById("client_0"));
        assert.verifySteps(['id: 1 props: {"chain":"never break","breadcrumbs":[]}']);
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
        assert.containsOnce(webClient, ".o_list_view");
        assert.strictEqual($(webClient.el).find(".breadcrumb-item").text(), "Partners");

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "clientAction",
        });
        assert.containsOnce(webClient, ".client_action");
        assert.strictEqual($(webClient.el).find(".breadcrumb-item").text(), "PartnersBlabla");
    });
});
