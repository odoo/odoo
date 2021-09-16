/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { legacyServiceProvider } from "@web/legacy/legacy_service_provider";
import { actionService } from "@web/webclient/actions/action_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { WebClient } from "@web/webclient/webclient";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { fakeTitleService } from "../helpers/mock_services";
import { getFixture, patchWithCleanup, triggerEvent } from "../helpers/utils";
import { session } from "@web/session";

const { Component, tags, mount } = owl;
const { xml } = tags;
const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

let baseConfig;

QUnit.module("WebClient", {
    async beforeEach() {
        serviceRegistry
            .add("action", actionService)
            .add("dialog", dialogService)
            .add("hotkey", hotkeyService)
            .add("legacy_service_provider", legacyServiceProvider)
            .add("menu", menuService)
            .add("notification", notificationService)
            .add("popover", popoverService)
            .add("title", fakeTitleService)
            .add("ui", uiService);
        baseConfig = { activateMockServer: true };
    },
});

QUnit.test("can be rendered", async (assert) => {
    assert.expect(1);
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.containsOnce(webClient.el, "header > nav.o_main_navbar");
    webClient.destroy();
});

QUnit.test("can render a main component", async (assert) => {
    assert.expect(1);
    class MyComponent extends Component {}
    MyComponent.template = xml`<span class="chocolate">MyComponent</span>`;
    clearRegistryWithCleanup(mainComponentRegistry);
    mainComponentRegistry.add("mycomponent", { Component: MyComponent });
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.containsOnce(webClient.el, ".chocolate");
    webClient.destroy();
});

QUnit.test("webclient for the superuser", async (assert) => {
    assert.expect(1);
    patchWithCleanup(session, { uid: 1 });
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.hasClass(webClient.el, "o_is_superuser");
    webClient.destroy();
});

QUnit.test("webclient for a non superuser", async (assert) => {
    assert.expect(1);
    patchWithCleanup(session, { uid: 2 });
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.doesNotHaveClass(webClient.el, "o_is_superuser");
    webClient.destroy();
});

QUnit.test("control-click propagation stopped on <a href/>", async (assert) => {
    assert.expect(8);

    patchWithCleanup(WebClient.prototype, {
        /** @param {MouseEvent} ev */
        onGlobalClick(ev) {
            this._super(ev);
            if (ev.ctrlKey) {
                assert.ok(
                    ev.defaultPrevented === false,
                    "the global click should not prevent the default behavior on ctrl-click an <a href/>"
                );
                // Necessary in order to prevent the test browser to open in new tab on ctrl-click
                ev.preventDefault();
            }
        },
    });

    class MyComponent extends Component {
        /** @param {MouseEvent} ev */
        onclick(ev) {
            assert.step(ev.ctrlKey ? "ctrl-click" : "click");
            // Necessary in order to prevent the test browser to open in new tab on ctrl-click
            ev.preventDefault();
        }
    }
    MyComponent.template = xml`<a href="#" class="MyComponent" t-on-click="onclick" />`;
    const target = getFixture();
    let env = await makeTestEnv(baseConfig);

    // Mount the component as standalone and control-click the <a href/>
    const standaloneComponent = await mount(MyComponent, { env, target });
    assert.verifySteps([]);
    await triggerEvent(standaloneComponent.el, "", "click", { ctrlKey: false });
    await triggerEvent(standaloneComponent.el, "", "click", { ctrlKey: true });
    assert.verifySteps(["click", "ctrl-click"]);
    standaloneComponent.destroy();

    // Register the component as a main one, mount the webclient and control-click the <a href/>
    clearRegistryWithCleanup(mainComponentRegistry);
    mainComponentRegistry.add("mycomponent", { Component: MyComponent });
    env = await makeTestEnv(baseConfig);
    const webClient = await mount(WebClient, { env, target });
    assert.verifySteps([]);
    await triggerEvent(webClient.el, ".MyComponent", "click", { ctrlKey: false });
    await triggerEvent(webClient.el, ".MyComponent", "click", { ctrlKey: true });
    assert.verifySteps(["click"]);
    webClient.destroy();
});
