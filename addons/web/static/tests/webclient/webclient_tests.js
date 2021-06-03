/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui_service";
import { legacyServiceProvider } from "@web/legacy/legacy_service_provider";
import { actionService } from "@web/webclient/actions/action_service";
import { hotkeyService } from "@web/webclient/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menu_service";
import { WebClient } from "@web/webclient/webclient";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { fakeTitleService, makeFakeUserService } from "../helpers/mock_services";
import { getFixture } from "../helpers/utils";

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
});

QUnit.test("webclient for the superuser", async (assert) => {
    assert.expect(1);
    const mockedSessionInfo = { uid: 1 };
    serviceRegistry.add("user", makeFakeUserService({ session_info: mockedSessionInfo }));
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.hasClass(webClient.el, "o_is_superuser");
});

QUnit.test("webclient for a non superuser", async (assert) => {
    assert.expect(1);
    const mockedSessionInfo = { uid: 2 };
    serviceRegistry.add("user", makeFakeUserService({ session_info: mockedSessionInfo }));
    const env = await makeTestEnv(baseConfig);
    const target = getFixture();
    const webClient = await mount(WebClient, { env, target });
    assert.doesNotHaveClass(webClient.el, "o_is_superuser");
});
