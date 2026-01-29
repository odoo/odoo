/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { click, getFixture, nextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

import { Component, onMounted, xml } from "@odoo/owl";

let serverData;
let target;
const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Client Actions");

    QUnit.test("can display client actions in Dialog", async function (assert) {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Dialog Test",
            target: "new",
            tag: "__test__client__action__",
            type: "ir.actions.client",
        });
        assert.containsOnce(target, ".modal .test_client_action");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "Dialog Test");
    });

    QUnit.test(
        "can display client actions in Dialog and close the dialog",
        async function (assert) {
            assert.expect(3);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                name: "Dialog Test",
                target: "new",
                tag: "__test__client__action__",
                type: "ir.actions.client",
            });
            assert.containsOnce(target, ".modal .test_client_action");
            assert.strictEqual(target.querySelector(".modal-title").textContent, "Dialog Test");
            target.querySelector(".modal footer .btn.btn-primary").click();
            await nextTick();
            assert.containsNone(target, ".modal .test_client_action");
        }
    );

    QUnit.test("can display client actions as main, then in Dialog", async function (assert) {
        assert.expect(3);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "__test__client__action__");
        assert.containsOnce(target, ".o_action_manager .test_client_action");
        await doAction(webClient, {
            target: "new",
            tag: "__test__client__action__",
            type: "ir.actions.client",
        });
        assert.containsOnce(target, ".o_action_manager .test_client_action");
        assert.containsOnce(target, ".modal .test_client_action");
    });

    QUnit.test(
        "can display client actions in Dialog, then as main destroys Dialog",
        async function (assert) {
            assert.expect(4);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                target: "new",
                tag: "__test__client__action__",
                type: "ir.actions.client",
            });
            assert.containsOnce(target, ".test_client_action");
            assert.containsOnce(target, ".modal .test_client_action");
            await doAction(webClient, "__test__client__action__");
            assert.containsOnce(target, ".test_client_action");
            assert.containsNone(target, ".modal .test_client_action");
        }
    );

    QUnit.test("soft_reload will refresh data", async (assert) => {
        const mockRPC = async function (route, args) {
            if (route === "/web/dataset/call_kw/partner/web_search_read") {
                assert.step("web_search_read");
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.verifySteps(["web_search_read"]);
        await doAction(webClient, "soft_reload");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("soft_reload a form view", async (assert) => {
        const mockRPC = async function (route, { args }) {
            if (route === "/web/dataset/call_kw/partner/web_read") {
                assert.step(`read ${args[0][0]}`);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            name: "Partners",
            res_model: "partner",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            type: "ir.actions.act_window",
        });

        await click(target.querySelector(".o_data_row .o_data_cell"));
        await click(target, ".o_form_view .o_pager_next");
        assert.verifySteps([
            "read 1",
            "read 2",
        ])
        await doAction(webClient, "soft_reload");
        assert.verifySteps(["read 2"]);
    });

    QUnit.test("soft_reload when there is no controller", async (assert) => {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "soft_reload");
        assert.ok(true, "No ControllerNotFoundError when there is no controller to restore");
    });

    QUnit.test("can execute client actions from tag name", async function (assert) {
        assert.expect(4);
        class ClientAction extends Component {}
        ClientAction.template = xml`<div class="o_client_action_test">Hello World</div>`;
        actionRegistry.add("HelloWorldTest", ClientAction);

        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, "HelloWorldTest");
        assert.containsNone(
            document.body,
            ".o_control_panel",
            "shouldn't have rendered a control panel"
        );
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus"]);
    });

    QUnit.test("async client action (function) returning another action", async function (assert) {
        assert.expect(1);

        registry.category("actions").add("my_action", async () => {
            await Promise.resolve();
            return 1; // execute action 1
        });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "my_action");
        assert.containsOnce(target, ".o_kanban_view");
    });

    QUnit.test(
        "'CLEAR-UNCOMMITTED-CHANGES' is not triggered for function client actions",
        async function (assert) {
            assert.expect(2);

            registry.category("actions").add("my_action", async () => {
                assert.step("my_action");
            });

            const webClient = await createWebClient({ serverData });
            webClient.env.bus.addEventListener("CLEAR-UNCOMMITTED-CHANGES", () => {
                assert.step("CLEAR-UNCOMMITTED-CHANGES");
            });

            await doAction(webClient, "my_action");
            assert.verifySteps(["my_action"]);
        }
    );

    QUnit.test("ClientAction receives breadcrumbs and exports title", async (assert) => {
        assert.expect(4);
        class ClientAction extends Component {
            setup() {
                this.breadcrumbTitle = "myOwlAction";
                const { breadcrumbs } = this.env.config;
                assert.strictEqual(breadcrumbs.length, 2);
                assert.strictEqual(breadcrumbs[0].name, "Favorite Ponies");
                onMounted(() => {
                    this.env.config.setDisplayName(this.breadcrumbTitle);
                });
            }
            onClick() {
                this.breadcrumbTitle = "newOwlTitle";
                this.env.config.setDisplayName(this.breadcrumbTitle);
            }
        }
        ClientAction.template = xml`<div class="my_owl_action" t-on-click="onClick">owl client action</div>`;
        actionRegistry.add("OwlClientAction", ClientAction);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 8);
        await doAction(webClient, "OwlClientAction");
        assert.containsOnce(target, ".my_owl_action");
        await click(target, ".my_owl_action");
        await doAction(webClient, 3);
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Favorite PoniesnewOwlTitlePartners"
        );
    });

    QUnit.test("ClientAction receives arbitrary props from doAction", async (assert) => {
        assert.expect(1);
        class ClientAction extends Component {
            setup() {
                assert.strictEqual(this.props.division, "bell");
            }
        }
        ClientAction.template = xml`<div class="my_owl_action"></div>`;
        actionRegistry.add("OwlClientAction", ClientAction);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "OwlClientAction", {
            props: { division: "bell" },
        });
    });

    QUnit.test("test display_notification client action", async function (assert) {
        assert.expect(6);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "display_notification",
            params: {
                title: "title",
                message: "message",
                sticky: true,
            },
        });
        await nextTick(); // wait for the notification to be displayed
        const notificationSelector = ".o_notification_manager .o_notification";
        assert.containsOnce(
            document.body,
            notificationSelector,
            "a notification should be present"
        );
        const notificationElement = document.body.querySelector(notificationSelector);
        assert.strictEqual(
            notificationElement.querySelector(".o_notification_title").textContent,
            "title",
            "the notification should have the correct title"
        );
        assert.strictEqual(
            notificationElement.querySelector(".o_notification_content").textContent,
            "message",
            "the notification should have the correct message"
        );
        assert.containsOnce(target, ".o_kanban_view");
        await testUtils.dom.click(notificationElement.querySelector(".o_notification_close"));
        assert.containsNone(
            document.body,
            notificationSelector,
            "the notification should be destroy "
        );
    });

    QUnit.test("test display_notification client action with links", async function (assert) {
        assert.expect(8);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "display_notification",
            params: {
                title: "title",
                message: "message %s <R&D>",
                sticky: true,
                links: [
                    {
                        label: "test <R&D>",
                        url: "#action={action.id}&id={order.id}&model=purchase.order",
                    },
                ],
            },
        });
        await nextTick(); // wait for the notification to be displayed
        const notificationSelector = ".o_notification_manager .o_notification";
        assert.containsOnce(
            document.body,
            notificationSelector,
            "a notification should be present"
        );
        let notificationElement = document.body.querySelector(notificationSelector);
        assert.strictEqual(
            notificationElement.querySelector(".o_notification_title").textContent,
            "title",
            "the notification should have the correct title"
        );
        assert.strictEqual(
            notificationElement.querySelector(".o_notification_content").textContent,
            "message test <R&D> <R&D>",
            "the notification should have the correct message"
        );
        assert.containsOnce(target, ".o_kanban_view");
        await testUtils.dom.click(notificationElement.querySelector(".o_notification_close"));
        assert.containsNone(
            document.body,
            notificationSelector,
            "the notification should be destroy "
        );

        // display_notification without title
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "display_notification",
            params: {
                message: "message %s <R&D>",
                sticky: true,
                links: [
                    {
                        label: "test <R&D>",
                        url: "#action={action.id}&id={order.id}&model=purchase.order",
                    },
                ],
            },
        });
        await nextTick(); // wait for the notification to be displayed
        assert.containsOnce(
            document.body,
            notificationSelector,
            "a notification should be present"
        );
        notificationElement = document.body.querySelector(notificationSelector);
        assert.containsNone(
            notificationElement,
            ".o_notification_title",
            "the notification should not have title"
        );
    });

    QUnit.test("test next action on display_notification client action", async function (assert) {
        const webClient = await createWebClient({ serverData });
        const options = {
            onClose: function () {
                assert.step("onClose");
            },
        };
        await doAction(
            webClient,
            {
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    title: "title",
                    message: "message",
                    sticky: true,
                    next: {
                        type: "ir.actions.act_window_close",
                    },
                },
            },
            options
        );
        await nextTick(); // wait for the notification to be displayed
        const notificationSelector = ".o_notification_manager .o_notification";
        assert.containsOnce(
            document.body,
            notificationSelector,
            "a notification should be present"
        );
        assert.verifySteps(["onClose"]);
    });

    QUnit.test("test reload client action", async function (assert) {
        patchWithCleanup(browser.location, {
            assign: (url) => {
                assert.step(url);
            },
            origin: "",
            hash: "#test=42",
        });

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "reload",
        });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "reload",
            params: {
                action_id: 2,
            },
        });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "reload",
            params: {
                menu_id: 1,
            },
        });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "reload",
            params: {
                action_id: 1,
                menu_id: 2,
            },
        });
        assert.verifySteps([
            "/web/tests?reload=true#test=42",
            "/web/tests?reload=true#action=2",
            "/web/tests?reload=true#menu_id=1",
            "/web/tests?reload=true#menu_id=2&action=1",
        ]);
    });
});
