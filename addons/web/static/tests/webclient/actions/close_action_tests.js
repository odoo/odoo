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

import { formView } from "@web/views/form/form_view";
import { listView } from "../../../src/views/list/list_view";

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
        let form;
        patchWithCleanup(formView.Controller.prototype, {
            setup() {
                this._super(...arguments);
                form = this;
            },
        });
        const webClient = await createWebClient({ serverData });
        function onClose() {
            assert.step("on_close");
        }
        // open a new dialog form
        await doAction(webClient, 5, { onClose });
        assert.containsOnce(target, ".modal");
        form.env.config.historyBack();
        assert.verifySteps(["on_close"], "should have called the on_close handler");
        await nextTick();
        assert.containsNone(target, ".modal");
    });

    QUnit.test("history back called within on_close", async function (assert) {
        assert.expect(7);
        let list;
        patchWithCleanup(listView.Controller.prototype, {
            setup() {
                this._super(...arguments);
                list = this;
            },
        });
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");

        function onClose() {
            list.env.config.historyBack();
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
            let list;
            patchWithCleanup(listView.Controller.prototype, {
                setup() {
                    this._super(...arguments);
                    list = this;
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
            list.env.config.historyBack();
            assert.verifySteps(["on_close"], "should have called the on_close handler");
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_list_view");
            assert.containsNone(target, ".modal");
        }
    );

    QUnit.test("web client is not deadlocked when a view crashes", async function (assert) {
        assert.expect(3);
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
        await testUtils.dom.click($(target).find(".o_list_view .o_data_cell:first"));
        await legacyExtraNextTick();
        readOnFirstRecordDef.reject("not working as intended");
        await nextTick();
        assert.containsOnce(target, ".o_list_view", "there should still be a list view in dom");
        // open another record, the read will not crash
        await testUtils.dom.click(
            $(target).find(".o_list_view .o_data_row:eq(2) .o_data_cell:first")
        );
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "there should not be a list view in dom");
        assert.containsOnce(target, ".o_form_view", "there should be a form view in dom");
    });
});
