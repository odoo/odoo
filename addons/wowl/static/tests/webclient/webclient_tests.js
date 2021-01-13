/** @odoo-module **/
const { Component, tags } = owl;
import { WebClient } from "../../src/webclient/webclient";
import { Registry } from "../../src/core/registry";
import { actionManagerService } from "../../src/action_manager/action_manager";
import { notificationService } from "../../src/notifications/notification_service";
import { mount, makeTestEnv } from "../helpers/utility";
import { menusService } from "../../src/services/menus";
import { fakeTitleService } from "../helpers/mocks";
const { xml } = tags;
let baseConfig;
QUnit.module("Web Client", {
  async beforeEach() {
    const serviceRegistry = new Registry();
    serviceRegistry
      .add(actionManagerService.name, actionManagerService)
      .add(notificationService.name, notificationService)
      .add(fakeTitleService.name, fakeTitleService)
      .add("menus", menusService);
    baseConfig = { serviceRegistry, activateMockServer: true };
  },
});
QUnit.test("can be rendered", async (assert) => {
  assert.expect(1);
  const env = await makeTestEnv(baseConfig);
  const webClient = await mount(WebClient, { env });
  assert.containsOnce(webClient.el, "header > nav.o_main_navbar");
  webClient.destroy();
});
QUnit.test("can render a main component", async (assert) => {
  assert.expect(1);
  class MyComponent extends Component {}
  MyComponent.template = xml`<span class="chocolate">MyComponent</span>`;
  const mainComponentRegistry = new Registry();
  mainComponentRegistry.add("mycomponent", MyComponent);
  const env = await makeTestEnv({ ...baseConfig, mainComponentRegistry });
  const webClient = await mount(WebClient, { env });
  assert.containsOnce(webClient.el, ".chocolate");
  webClient.destroy();
});
