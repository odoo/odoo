/** @odoo-module **/

import testUtils from "web.test_utils";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    nextTick,
    patchWithCleanup,
} from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { registerCleanup } from "../../helpers/cleanup";
import FormController from "web.FormController";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import ListController from "web.ListController";
import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let serverData;
let target;
QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module('"ir.actions.act_window_close" actions');

    QUnit.test("close the currently opened dialog", async function (assert) {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        // execute an action in target="new"
        await doAction(webClient, 5);
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view",
            "should have rendered a form view in a modal"
        );
        // execute an 'ir.actions.act_window_close' action
        await doAction(webClient, {
            type: "ir.actions.act_window_close",
        });
        assert.containsNone(document.body, ".o_technical_modal", "should have closed the modal");
    });

    QUnit.test("close dialog by clicking on the header button", async function (assert) {
        assert.expect(5);
        const webClient = await createWebClient({ serverData });
        // execute an action in target="new"
        function onClose() {
            assert.step("on_close");
        }
        await doAction(webClient, 5, { onClose });
        assert.containsOnce(target, ".o_dialog_container .o_dialog");
        await click(target.querySelector(".o_dialog_container .o_dialog .modal-header button"));
        assert.containsNone(target, ".o_dialog_container .o_dialog");
        assert.verifySteps(["on_close"]);

        // execute an 'ir.actions.act_window_close' action
        // should not call 'on_close' as it was already called.
        await doAction(webClient, { type: "ir.actions.act_window_close" });
        assert.verifySteps([]);
    });

    QUnit.test('execute "on_close" only if there is no dialog to close', async function (assert) {
        assert.expect(3);
        const webClient = await createWebClient({ serverData });
        // execute an action in target="new"
        await doAction(webClient, 5);
        function onClose() {
            assert.step("on_close");
        }
        const options = { onClose };
        // execute an 'ir.actions.act_window_close' action
        // should not call 'on_close' as there is a dialog to close
        await doAction(webClient, { type: "ir.actions.act_window_close" }, options);
        assert.verifySteps([]);
        // execute again an 'ir.actions.act_window_close' action
        // should call 'on_close' as there is no dialog to close
        await doAction(webClient, { type: "ir.actions.act_window_close" }, options);
        assert.verifySteps(["on_close"]);
    });

    QUnit.test("close action with provided infos", async function (assert) {
        assert.expect(1);
        const webClient = await createWebClient({ serverData });
        const options = {
            onClose: function (infos) {
                assert.strictEqual(
                    infos,
                    "just for testing",
                    "should have the correct close infos"
                );
            },
        };
        await doAction(
            webClient,
            {
                type: "ir.actions.act_window_close",
                infos: "just for testing",
            },
            options
        );
    });

    QUnit.test("history back calls on_close handler of dialog action", async function (assert) {
        assert.expect(4);
        let controller;
        patchWithCleanup(FormController.prototype, {
            init() {
                this._super(...arguments);
                controller = this;
            },
        });
        const webClient = await createWebClient({ serverData });
        function onClose() {
            assert.step("on_close");
        }
        // open a new dialog form
        await doAction(webClient, 5, { onClose });
        assert.containsOnce(target, ".modal");
        controller.trigger_up("history_back");
        assert.verifySteps(["on_close"], "should have called the on_close handler");
        await nextTick();
        assert.containsNone(target, ".modal");
    });

    QUnit.test("history back called within on_close", async function (assert) {
        assert.expect(7);
        let controller;
        patchWithCleanup(ListController.prototype, {
            init() {
                this._super(...arguments);
                controller = this;
            },
        });
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");

        function onClose() {
            controller.trigger_up("history_back");
            assert.step("on_close");
        }
        // open a new dialog form
        await doAction(webClient, 5, { onClose });

        await click(target, ".modal-header button.close");
        await nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".modal");
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps(["on_close"]);
    });

    QUnit.test(
        "history back calls on_close handler of dialog action with 2 breadcrumbs",
        async function (assert) {
            assert.expect(7);
            let controller;
            patchWithCleanup(ListController.prototype, {
                init() {
                    this._super(...arguments);
                    controller = this;
                },
            });
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1); // kanban
            await doAction(webClient, 3); // list
            assert.containsOnce(target, ".o_list_view");
            function onClose() {
                assert.step("on_close");
            }
            // open a new dialog form
            await doAction(webClient, 5, { onClose });
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".o_list_view");
            controller.trigger_up("history_back");
            assert.verifySteps(["on_close"], "should have called the on_close handler");
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_list_view");
            assert.containsNone(target, ".modal");
        }
    );

    QUnit.test(
        "history back calls on_close handler of dialog action with 2 breadcrumbs (2)",
        async function (assert) {
            assert.expect(7);
            let pivot;
            patchWithCleanup(pivotView.Controller.prototype, {
                setup() {
                    this._super(...arguments);
                    pivot = this;
                },
            });
            serverData.views["partner,false,pivot"] = "<pivot/>";
            serviceRegistry.add("user", makeFakeUserService());
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1); // kanban
            await doAction(webClient, {
                id: 3,
                xml_id: "action_3",
                name: "Partners",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            }); // pivot
            assert.containsOnce(target, ".o_pivot_view");
            function onClose() {
                assert.step("on_close");
            }
            // open a new dialog form
            await doAction(webClient, 5, { onClose });
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".o_pivot_view");
            pivot.env.config.historyBack();
            assert.verifySteps(["on_close"], "should have called the on_close handler");
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_pivot_view");
            assert.containsNone(target, ".modal");
        }
    );

    QUnit.test("web client is not deadlocked when a view crashes", async function (assert) {
        assert.expect(6);
        const handler = (ev) => {
            assert.step("error");
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => window.removeEventListener("unhandledrejection", handler));
        patchWithCleanup(QUnit, {
            onUnhandledRejection: () => {},
        });

        const readOnFirstRecordDef = testUtils.makeTestPromise();
        const mockRPC = (route, args) => {
            if (args.method === "read" && args.args[0][0] === 1) {
                return readOnFirstRecordDef;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // open first record in form view. this will crash and will not
        // display a form view
        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:first"));
        assert.verifySteps([]);
        await legacyExtraNextTick();
        readOnFirstRecordDef.reject(new Error("not working as intended"));
        await nextTick();
        assert.verifySteps(["error"])
        assert.containsOnce(target, ".o_list_view", "there should still be a list view in dom");
        // open another record, the read will not crash
        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:eq(2)"));
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "there should not be a list view in dom");
        assert.containsOnce(target, ".o_form_view", "there should be a form view in dom");
    });
});
