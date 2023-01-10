/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import core from "web.core";
import AbstractAction from "web.AbstractAction";
import testUtils from "web.test_utils";
import { registerCleanup } from "../../helpers/cleanup";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    nextTick,
    patchWithCleanup,
} from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

import { Component, xml } from "@odoo/owl";

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

    QUnit.test("can execute client actions from tag name (legacy)", async function (assert) {
        // remove this test as soon as legacy Widgets are no longer supported
        assert.expect(4);
        const ClientAction = AbstractAction.extend({
            start: function () {
                this.$el.text("Hello World");
                this.$el.addClass("o_client_action_test");
            },
        });
        const mockRPC = async function (route, args) {
            assert.step((args && args.method) || route);
        };
        core.action_registry.add("HelloWorldTestLeg", ClientAction);
        registerCleanup(() => delete core.action_registry.map.HelloWorldTestLeg);
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, "HelloWorldTestLeg");
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

    QUnit.test("client action with control panel (legacy)", async function (assert) {
        assert.expect(4);
        // LPE Fixme: at this time we don't really know the API that wowl ClientActions implement
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            start() {
                this.$(".o_content").text("Hello World");
                this.$el.addClass("o_client_action_test");
                this.controlPanelProps.title = "Hello";
                return this._super.apply(this, arguments);
            },
        });
        core.action_registry.add("HelloWorldTest", ClientAction);
        registerCleanup(() => delete core.action_registry.map.HelloWorldTest);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "HelloWorldTest");
        assert.strictEqual(
            $(".o_control_panel:visible").length,
            1,
            "should have rendered a control panel"
        );
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            1,
            "there should be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(".o_control_panel .breadcrumb-item").text(),
            "Hello",
            "breadcrumbs should still display the title of the controller"
        );
        assert.strictEqual(
            $(target).find(".o_client_action_test .o_content").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
    });

    QUnit.test("state is pushed for client action (legacy)", async function (assert) {
        assert.expect(6);
        const ClientAction = AbstractAction.extend({
            getTitle: function () {
                return "a title";
            },
            getState: function () {
                return { foo: "baz" };
            },
        });
        const pushState = browser.history.pushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    pushState(...arguments);
                    assert.step("push_state");
                },
            }),
        });

        core.action_registry.add("HelloWorldTest", ClientAction);
        registerCleanup(() => delete core.action_registry.map.HelloWorldTest);
        const webClient = await createWebClient({ serverData });
        let currentTitle = webClient.env.services.title.current;
        assert.strictEqual(currentTitle, '{"zopenerp":"Odoo"}');
        let currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {});
        await doAction(webClient, "HelloWorldTest");
        currentTitle = webClient.env.services.title.current;
        assert.strictEqual(currentTitle, '{"zopenerp":"Odoo","action":"a title"}');
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {
            action: "HelloWorldTest",
            foo: "baz",
        });
        assert.verifySteps(["push_state"]);
    });

    QUnit.test("action can use a custom control panel (legacy)", async function (assert) {
        assert.expect(1);
        class CustomControlPanel extends Component {}
        CustomControlPanel.template = xml`
        <div class="custom-control-panel">My custom control panel</div>
      `;
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            config: {
                ControlPanel: CustomControlPanel,
            },
        });
        core.action_registry.add("HelloWorldTest", ClientAction);
        registerCleanup(() => delete core.action_registry.map.HelloWorldTest);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "HelloWorldTest");
        assert.containsOnce(target, ".custom-control-panel", "should have a custom control panel");
    });

    QUnit.test("breadcrumb is updated on title change (legacy)", async function (assert) {
        assert.expect(2);
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            events: {
                click: function () {
                    this.updateControlPanel({ title: "new title" });
                },
            },
            start: async function () {
                this.$(".o_content").text("Hello World");
                this.$el.addClass("o_client_action_test");
                this.controlPanelProps.title = "initial title";
                await this._super.apply(this, arguments);
            },
        });
        core.action_registry.add("HelloWorldTest", ClientAction);
        registerCleanup(() => delete core.action_registry.map.HelloWorldTest);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "HelloWorldTest");
        assert.strictEqual(
            $("ol.breadcrumb").text(),
            "initial title",
            "should have initial title as breadcrumb content"
        );
        await testUtils.dom.click($(target).find(".o_client_action_test"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $("ol.breadcrumb").text(),
            "new title",
            "should have updated title as breadcrumb content"
        );
    });

    QUnit.test("client actions can have breadcrumbs (legacy)", async function (assert) {
        assert.expect(4);
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            init(parent, action) {
                action.display_name = "Goldeneye";
                this._super.apply(this, arguments);
            },
            start() {
                this.$el.addClass("o_client_action_test");
                return this._super.apply(this, arguments);
            },
        });
        const ClientAction2 = AbstractAction.extend({
            hasControlPanel: true,
            init(parent, action) {
                action.display_name = "No time for sweetness";
                this._super.apply(this, arguments);
            },
            start() {
                this.$el.addClass("o_client_action_test_2");
                return this._super.apply(this, arguments);
            },
        });
        core.action_registry.add("ClientAction", ClientAction);
        core.action_registry.add("ClientAction2", ClientAction2);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "ClientAction");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(
            target.querySelector(".breadcrumb-item.active").textContent,
            "Goldeneye"
        );
        await doAction(webClient, "ClientAction2", { clearBreadcrumbs: false });
        assert.containsN(target, ".breadcrumb-item", 2);
        assert.strictEqual(
            target.querySelector(".breadcrumb-item.active").textContent,
            "No time for sweetness"
        );
        delete core.action_registry.map.ClientAction;
        delete core.action_registry.map.ClientAction2;
    });

    QUnit.test("client action restore scrollbar (legacy)", async function (assert) {
        assert.expect(7);
        const ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            init(parent, action) {
                action.display_name = "Title1";
                this._super.apply(this, arguments);
            },
            async start() {
                for (let i = 0; i < 100; i++) {
                    const content = document.createElement("div");
                    content.innerText = "Paper company";
                    content.className = "lorem";
                    this.el.querySelector(".o_content").appendChild(content);
                }
                await this._super(arguments);
            },
        });
        const ClientAction2 = AbstractAction.extend({
            hasControlPanel: true,
            init(parent, action) {
                action.display_name = "Title2";
                this._super.apply(this, arguments);
            },
            start() {
                return this._super.apply(this, arguments);
            },
        });
        core.action_registry.add("ClientAction", ClientAction);
        core.action_registry.add("ClientAction2", ClientAction2);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "ClientAction");
        assert.containsOnce(target, ".breadcrumb-item");
        assert.strictEqual(target.querySelector(".breadcrumb-item.active").textContent, "Title1");

        target.querySelector(".lorem:last-child").scrollIntoView();
        const scrollPosition = target.querySelector(".o_content").scrollTop;
        assert.ok(scrollPosition > 0);
        await doAction(webClient, "ClientAction2", { clearBreadcrumbs: false });
        assert.containsN(target, ".breadcrumb-item", 2);
        assert.strictEqual(target.querySelector(".breadcrumb-item.active").textContent, "Title2");

        await click(target.querySelector(".breadcrumb-item:first-child"));
        assert.strictEqual(target.querySelector(".breadcrumb-item.active").textContent, "Title1");

        assert.strictEqual(
            target.querySelector(".o_content").scrollTop,
            scrollPosition,
            "Should restore the scroll"
        );
        delete core.action_registry.map.ClientAction;
        delete core.action_registry.map.ClientAction2;
    });

    QUnit.test("ClientAction receives breadcrumbs and exports title (wowl)", async (assert) => {
        assert.expect(4);
        class ClientAction extends Component {
            setup() {
                this.breadcrumbTitle = "myOwlAction";
                const { breadcrumbs } = this.env.config;
                assert.strictEqual(breadcrumbs.length, 2);
                assert.strictEqual(breadcrumbs[0].name, "Favorite Ponies");
                owl.onMounted(() => {
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
            target.querySelector(".breadcrumb").textContent,
            "Favorite PoniesnewOwlTitlePartners"
        );
    });

    QUnit.test("ClientAction receives arbitrary props from doAction (wowl)", async (assert) => {
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

    QUnit.test("ClientAction receives arbitrary props from doAction (legacy)", async (assert) => {
        assert.expect(1);
        const ClientAction = AbstractAction.extend({
            init(parent, action, options) {
                assert.strictEqual(options.division, "bell");
                this._super.apply(this, arguments);
            },
        });
        core.action_registry.add("ClientAction", ClientAction);
        registerCleanup(() => delete core.action_registry.map.ClientAction);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "ClientAction", {
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
        const notificationSelector = ".o_notification_manager .o_notification";
        assert.containsOnce(
            document.body,
            notificationSelector,
            "a notification should be present"
        );
        assert.verifySteps(["onClose"]);
    });
});
