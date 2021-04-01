/** @odoo-module **/

import { WebClient } from "../../src/webclient/webclient";
import { Registry } from "../../src/core/registry";
import { actionService } from "../../src/actions/action_service";
import { notificationService } from "../../src/notifications/notification_service";
import { getFixture, makeTestEnv } from "../helpers/index";
import { menuService } from "../../src/services/menu_service";
import { fakeTitleService } from "../helpers/mocks";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { uiService } from "../../src/services/ui_service";

const { Component, tags, mount } = owl;
const { xml } = tags;

let baseConfig;

QUnit.module("Web Client", {
  async beforeEach() {
    const serviceRegistry = new Registry();
    serviceRegistry
      .add("action", actionService)
      .add("hotkey", hotkeyService)
      .add("ui", uiService)
      .add("notification", notificationService)
      .add("title", fakeTitleService)
      .add("menu", menuService);
    baseConfig = { serviceRegistry, activateMockServer: true };
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
  const mainComponentRegistry = new Registry();
  mainComponentRegistry.add("mycomponent", MyComponent);
  const env = await makeTestEnv({ ...baseConfig, mainComponentRegistry });
  const target = getFixture();
  const webClient = await mount(WebClient, { env, target });
  assert.containsOnce(webClient.el, ".chocolate");
});
