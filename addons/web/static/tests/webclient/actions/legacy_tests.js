/** @odoo-module **/

import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import ListController from "web.ListController";
import ListView from 'web.ListView';
import { click, legacyExtraNextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

import { ClientActionAdapter } from "@web/legacy/action_adapters";
import { useDebugMenu } from "@web/core/debug/debug_menu";
import { debugService } from "@web/core/debug/debug_service";

import ControlPanel from "web.ControlPanel";
import core from "web.core";
import AbstractAction from "web.AbstractAction";

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
                useDebugMenu("custom", { widget: this });
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
        registry.category("services").add("debug", debugService);
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
                const views = action.views.map((view) => ([view.viewID, view.type]));
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
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "Integer field", type: "integer", group_operator: 'sum'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    foo: "yop",
                    int_field: 3,
                }, {
                    id: 2,
                    display_name: "second record",
                    foo: "lalala",
                    int_field: 5,
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                    int_field: 2,
                }],
            }
        };
        const views = {
            "partner,1,list": '<list><field name="foo"/></list>',
            'partner,2,kanban': '<kanban></kanban>',
            "partner,3,form": `<form></form>`,
            'partner,false,search': '<search></search>',
        };
        const serverData = { models, views };

        const webClient = await createWebClient({
            serverData,
        });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "list"], [2, "kanban"], [3, "form"]],

        });
    });
});
