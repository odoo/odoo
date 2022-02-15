/** @odoo-module **/

import testUtils from "web.test_utils";
import core from "web.core";
import AbstractAction from "web.AbstractAction";
import { registry } from "@web/core/registry";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    patchWithCleanup,
    makeDeferred,
    nextTick,
} from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { registerCleanup } from "../../helpers/cleanup";
import { errorService } from "@web/core/errors/error_service";
import { useService } from "@web/core/utils/hooks";
import { ClientErrorDialog } from "@web/core/errors/error_dialogs";

const { Component, onMounted, xml } = owl;

let serverData;
let target;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module('Actions in target="new"');

    QUnit.skip('can execute act_window actions in target="new"', async function (assert) {
        assert.expect(8);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 5);
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view",
            "should have rendered a form view in a modal"
        );
        assert.hasClass(
            $(".o_technical_modal .modal-body")[0],
            "o_act_window",
            "dialog main element should have classname 'o_act_window'"
        );
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view o_form_editable",
            "form view should be in edit mode"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]);
    });

    QUnit.test("chained action on_close", async function (assert) {
        assert.expect(4);
        function onClose(closeInfo) {
            assert.strictEqual(closeInfo, "smallCandle");
            assert.step("Close Action");
        }
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 5, { onClose });
        // a target=new action shouldn't activate the on_close
        await doAction(webClient, 5);
        assert.verifySteps([]);
        // An act_window_close should trigger the on_close
        await doAction(webClient, { type: "ir.actions.act_window_close", infos: "smallCandle" });
        assert.verifySteps(["Close Action"]);
    });

    QUnit.skip("footer buttons are moved to the dialog footer", async function (assert) {
        assert.expect(3);
        serverData.views["partner,false,form"] = `
      <form>
        <field name="display_name"/>
        <footer>
          <button string="Create" type="object" class="infooter"/>
        </footer>
      </form>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 5);
        assert.containsNone(
            $(".o_technical_modal .modal-body")[0],
            "button.infooter",
            "the button should not be in the body"
        );
        assert.containsOnce(
            $(".o_technical_modal .modal-footer")[0],
            "button.infooter",
            "the button should be in the footer"
        );
        assert.containsOnce(
            $(".o_technical_modal .modal-footer")[0],
            "button",
            "the modal footer should only contain one button"
        );
    });

    QUnit.skip("Button with `close` attribute closes dialog", async function (assert) {
        assert.expect(19);
        serverData.views = {
            "partner,false,form": `
        <form>
          <header>
            <button string="Open dialog" name="5" type="action"/>
          </header>
        </form>
      `,
            "partner,view_ref,form": `
          <form>
            <footer>
              <button string="I close the dialog" name="some_method" type="object" close="1"/>
            </footer>
          </form>
      `,
            "partner,false,search": "<search></search>",
        };
        serverData.actions[4] = {
            id: 4,
            name: "Partners Action 4",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
        serverData.actions[5] = {
            id: 5,
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [["view_ref", "form"]],
        };
        const mockRPC = async (route, args) => {
            assert.step(route);
            if (route === "/web/dataset/call_button" && args.method === "some_method") {
                return {
                    tag: "display_notification",
                    type: "ir.actions.client",
                };
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        assert.verifySteps(["/web/webclient/load_menus"]);
        await doAction(webClient, 4);
        assert.verifySteps([
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/onchange",
        ]);
        await testUtils.dom.click(`button[name="5"]`);
        assert.verifySteps([
            "/web/dataset/call_kw/partner/create",
            "/web/dataset/call_kw/partner/read",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/onchange",
        ]);
        await legacyExtraNextTick();
        assert.strictEqual($(".modal").length, 1, "It should display a modal");
        await testUtils.dom.click(`button[name="some_method"]`);
        assert.verifySteps([
            "/web/dataset/call_kw/partner/create",
            "/web/dataset/call_kw/partner/read",
            "/web/dataset/call_button",
            "/web/dataset/call_kw/partner/read",
        ]);
        await legacyExtraNextTick();
        assert.strictEqual($(".modal").length, 0, "It should have closed the modal");
    });

    QUnit.test('on_attach_callback is called for actions in target="new"', async function (assert) {
        assert.expect(3);
        const ClientAction = AbstractAction.extend({
            on_attach_callback: function () {
                assert.step("on_attach_callback");
                assert.containsOnce(
                    document.body,
                    ".modal .o_test",
                    "should have rendered the client action in a dialog"
                );
            },
            start: function () {
                this.$el.addClass("o_test");
            },
        });
        core.action_registry.add("test", ClientAction);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            tag: "test",
            target: "new",
            type: "ir.actions.client",
        });
        assert.verifySteps(["on_attach_callback"]);
        delete core.action_registry.map.test;
    });

    QUnit.skip(
        'footer buttons are updated when having another action in target "new"',
        async function (assert) {
            serverData.views["partner,false,form"] =
                "<form>" +
                '<field name="display_name"/>' +
                "<footer>" +
                '<button string="Create" type="object" class="infooter"/>' +
                "</footer>" +
                "</form>";
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 5);
            assert.containsNone(target, '.o_technical_modal .modal-body button[special="save"]');
            assert.containsNone(target, ".o_technical_modal .modal-body button.infooter");
            assert.containsOnce(target, ".o_technical_modal .modal-footer button.infooter");
            assert.containsOnce(target, ".o_technical_modal .modal-footer button");
            await doAction(webClient, 25);
            assert.containsNone(target, ".o_technical_modal .modal-body button.infooter");
            assert.containsNone(target, ".o_technical_modal .modal-footer button.infooter");
            assert.containsNone(target, '.o_technical_modal .modal-body button[special="save"]');
            assert.containsOnce(target, '.o_technical_modal .modal-footer button[special="save"]');
            assert.containsOnce(target, ".o_technical_modal .modal-footer button");
        }
    );

    QUnit.skip(
        'buttons of client action in target="new" and transition to MVC action',
        async function (assert) {
            const ClientAction = AbstractAction.extend({
                renderButtons($target) {
                    const button = document.createElement("button");
                    button.setAttribute("class", "o_stagger_lee");
                    $target[0].appendChild(button);
                },
            });
            core.action_registry.add("test", ClientAction);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                tag: "test",
                target: "new",
                type: "ir.actions.client",
            });
            assert.containsOnce(target, ".modal footer button.o_stagger_lee");
            assert.containsNone(target, '.modal footer button[special="save"]');
            await doAction(webClient, 25);
            assert.containsNone(target, ".modal footer button.o_stagger_lee");
            assert.containsOnce(target, '.modal footer button[special="save"]');
            delete core.action_registry.map.test;
        }
    );

    QUnit.skip(
        'button with confirm attribute in act_window action in target="new"',
        async function (assert) {
            serverData.actions[999] = {
                id: 999,
                name: "A window action",
                res_model: "partner",
                target: "new",
                type: "ir.actions.act_window",
                views: [[999, "form"]],
            };
            serverData.views["partner,999,form"] = `
            <form>
                <button name="method" string="Call method" type="object" confirm="Are you sure?"/>
            </form>`;
            serverData.views["partner,1000,form"] = `<form>Another action</form>`;

            const mockRPC = (route, args) => {
                if (args.method === "method") {
                    return Promise.resolve({
                        id: 1000,
                        name: "Another window action",
                        res_model: "partner",
                        target: "new",
                        type: "ir.actions.act_window",
                        views: [[1000, "form"]],
                    });
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, 999);

            assert.containsOnce(document.body, ".modal button[name=method]");

            await testUtils.dom.click($(".modal button[name=method]"));

            assert.containsN(document.body, ".modal", 2);
            assert.strictEqual($(".modal:last .modal-body").text(), "Are you sure?");

            await testUtils.dom.click($(".modal:last .modal-footer .btn-primary"));
            assert.containsOnce(document.body, ".modal");
            assert.strictEqual($(".modal:last .modal-body").text().trim(), "Another action");
        }
    );

    QUnit.test('actions in target="new" do not update page title', async function (assert) {
        const mockedTitleService = {
            start() {
                return {
                    setParts({ action }) {
                        if (action) {
                            assert.step(action);
                        }
                    },
                };
            },
        };
        registry.category("services").add("title", mockedTitleService);
        const webClient = await createWebClient({ serverData });

        // sanity check: execute an action in target="current"
        await doAction(webClient, 1);
        assert.verifySteps(["Partners Action 1"]);

        // execute an action in target="new"
        await doAction(webClient, 5);
        assert.verifySteps([]);
    });

    QUnit.test("do not commit a dialog in error", async (assert) => {
        assert.expect(6);

        const handler = (ev) => {
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => window.removeEventListener("unhandledrejection", handler));

        patchWithCleanup(QUnit, {
            onUnhandledRejection: () => {},
        });

        class ErrorClientAction extends Component {
            setup() {
                throw new Error("my error");
            }
        }
        ErrorClientAction.template = xml`<div/>`;
        registry.category("actions").add("failing", ErrorClientAction);

        class ClientActionTargetNew extends Component {}
        ClientActionTargetNew.template = xml`<div class="my_action_new" />`;
        registry.category("actions").add("clientActionNew", ClientActionTargetNew);

        class ClientAction extends Component {
            setup() {
                this.action = useService("action");
            }
            async onClick() {
                try {
                    await this.action.doAction(
                        { type: "ir.actions.client", tag: "failing", target: "new" },
                        { onClose: () => assert.step("failing dialog closed") }
                    );
                } catch (e) {
                    assert.strictEqual(e.message, "my error");
                }
            }
        }
        ClientAction.template = xml`<div class="my_action" t-on-click="onClick" />`;
        registry.category("actions").add("clientAction", ClientAction);

        const errorDialogOpened = makeDeferred();
        patchWithCleanup(ClientErrorDialog.prototype, {
            setup() {
                this._super(...arguments);
                onMounted(() => errorDialogOpened.resolve());
            },
        });

        registry.category("services").add("error", errorService);
        const webClient = await createWebClient({});

        await doAction(webClient, { type: "ir.actions.client", tag: "clientAction" });
        await click(target, ".my_action");
        await errorDialogOpened;

        assert.containsOnce(target, ".modal");
        await click(target, ".modal-body button.btn-link");
        assert.ok(
            target.querySelector(".modal-body .o_error_detail").textContent.includes("my error")
        );

        await click(target, ".modal-footer button");
        assert.containsNone(target, ".modal");

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "clientActionNew",
            target: "new",
        });
        assert.containsOnce(target, ".modal .my_action_new");

        assert.verifySteps([]);
    });

    QUnit.test('breadcrumbs of actions in target="new"', async function (assert) {
        const webClient = await createWebClient({ serverData });

        // execute an action in target="current"
        await doAction(webClient, 1);
        assert.deepEqual(
            [...target.querySelectorAll(".breadcrumb-item")].map((i) => i.innerText),
            ["Partners Action 1"]
        );

        // execute an action in target="new" and a list view (s.t. there is a control panel)
        await doAction(webClient, {
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });
        assert.deepEqual(
            [...target.querySelectorAll(".modal .breadcrumb-item")].map((i) => i.innerText),
            ["Create a Partner"]
        );
    });

    QUnit.test('call switchView in an action in target="new"', async function (assert) {
        const webClient = await createWebClient({ serverData });

        // execute an action in target="current"
        await doAction(webClient, 4);
        assert.containsOnce(target, ".o_kanban_view");

        // execute an action in target="new" and a list view (s.t. we can call switchView)
        await doAction(webClient, {
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });
        assert.containsOnce(target, ".modal .o_list_view");
        assert.containsOnce(target, ".o_kanban_view");

        // click on a record in the dialog -> should do nothing as we can't switch view
        // in the dialog, and we don't want to switch view behind the dialog
        await click(target.querySelector(".modal .o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal .o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
    });

    QUnit.module('Actions in target="inline"');

    QUnit.skip(
        'form views for actions in target="inline" open in edit mode',
        async function (assert) {
            const mockRPC = async (route, args) => {
                assert.step(args.method || route);
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 6);
            assert.containsOnce(
                target,
                ".o_form_view.o_form_editable",
                "should have rendered a form view in edit mode"
            );
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "get_views",
                "read",
            ]);
        }
    );

    QUnit.skip("breadcrumbs and actions with target inline", async function (assert) {
        serverData.actions[4].views = [[false, "form"]];
        serverData.actions[4].target = "inline";
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        assert.containsNone(target, ".o_control_panel");
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.containsOnce(target, ".o_control_panel");
        assert.isVisible(target.querySelector(".o_control_panel"));
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partners Action 1",
            "should have only one current action visible in breadcrumbs"
        );
    });

    QUnit.module('Actions in target="fullscreen"');

    QUnit.test(
        'correctly execute act_window actions in target="fullscreen"',
        async function (assert) {
            serverData.actions[1].target = "fullscreen";
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);
            await nextTick(); // wait for the webclient template to be re-rendered
            assert.containsOnce(target, ".o_control_panel", "should have rendered a control panel");
            assert.containsOnce(target, ".o_kanban_view", "should have rendered a kanban view");
            assert.containsNone(target, ".o_main_navbar");
        }
    );

    QUnit.test('fullscreen on action change: back to a "current" action', async function (assert) {
        serverData.actions[1].target = "fullscreen";
        serverData.views[
            "partner,false,form"
        ] = `<form><button name="1" type="action" class="oe_stat_button" /></form>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 6);
        assert.containsOnce(target, ".o_main_navbar");
        await click(target.querySelector("button[name='1']"));
        await nextTick(); // wait for the webclient template to be re-rendered
        assert.containsNone(target, ".o_main_navbar");
        await click(target.querySelector(".breadcrumb li a"));
        await nextTick(); // wait for the webclient template to be re-rendered
        assert.containsOnce(target, ".o_main_navbar");
    });

    QUnit.test('fullscreen on action change: all "fullscreen" actions', async function (assert) {
        serverData.actions[6].target = "fullscreen";
        serverData.views[
            "partner,false,form"
        ] = `<form><button name="1" type="action" class="oe_stat_button" /></form>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 6);
        assert.isNotVisible(target.querySelector(".o_main_navbar"));
        await click(target.querySelector("button[name='1']"));
        assert.isNotVisible(target.querySelector(".o_main_navbar"));
        await click(target.querySelector(".breadcrumb li a"));
        assert.isNotVisible(target.querySelector(".o_main_navbar"));
    });

    QUnit.test(
        'fullscreen on action change: back to another "current" action',
        async function (assert) {
            serverData.menus = {
                root: { id: "root", children: [1], name: "root", appID: "root" },
                1: { id: 1, children: [], name: "MAIN APP", appID: 1, actionID: 6 },
            };
            serverData.actions[1].target = "fullscreen";
            serverData.views["partner,false,form"] =
                '<form><button name="24" type="action" class="oe_stat_button"/></form>';
            await createWebClient({ serverData });
            await nextTick(); // wait for the load state (default app)
            assert.containsOnce(target, "nav .o_menu_brand");
            assert.strictEqual(target.querySelector("nav .o_menu_brand").innerText, "MAIN APP");
            await click(target.querySelector("button[name='24']"));
            await nextTick(); // wait for the webclient template to be re-rendered
            assert.containsOnce(target, "nav .o_menu_brand");
            await click(target.querySelector("button[name='1']"));
            await nextTick(); // wait for the webclient template to be re-rendered
            assert.containsNone(target, "nav.o_main_navbar");
            await click(target.querySelectorAll(".breadcrumb li a")[1]);
            await nextTick(); // wait for the webclient template to be re-rendered
            assert.containsOnce(target, "nav .o_menu_brand");
            assert.strictEqual(target.querySelector("nav .o_menu_brand").innerText, "MAIN APP");
        }
    );

    QUnit.module('Actions in target="main"');

    QUnit.test('can execute act_window actions in target="main"', async function (assert) {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.containsOnce(target, ".o_kanban_view");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partners Action 1"
        );

        await doAction(webClient, {
            name: "Another Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            target: "main",
        });

        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Another Partner Action"
        );
    });

    QUnit.test('can switch view in an action in target="main"', async function (assert) {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "main",
        });

        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partner Action"
        );

        // open first record
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await legacyExtraNextTick();

        assert.containsOnce(target, ".o_form_view");
        assert.containsN(target, ".breadcrumb-item", 2);
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partner ActionFirst record"
        );
    });

    QUnit.test('can restore an action in target="main"', async function (assert) {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "main",
        });

        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partner Action"
        );

        // open first record
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsN(target, ".breadcrumb-item", 2);
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partner ActionFirst record"
        );

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        assert.containsN(target, ".breadcrumb-item", 3);

        // go back to form view
        await click(target.querySelectorAll(".breadcrumb-item")[1]);
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsN(target, ".breadcrumb-item", 2);
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb").textContent,
            "Partner ActionFirst record"
        );
    });
});
