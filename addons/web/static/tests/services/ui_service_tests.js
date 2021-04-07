/** @odoo-module **/

import { Registry } from "../../src/core/registry";
import { uiService, useActiveElement } from "../../src/services/ui_service";
import { BlockUI } from "../../src/webclient/block_ui/block_ui";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, nextTick } from "../helpers/utils";

const { mount } = owl;

let target;
let serviceRegistry;
let browser;
let baseConfig;

QUnit.module("UI", {
  async beforeEach() {
    target = getFixture();
    serviceRegistry = new Registry();
    serviceRegistry.add("ui", uiService);
    browser = { setTimeout: () => 1 };
    baseConfig = { serviceRegistry, browser };
  },
});

QUnit.test("block and unblock once ui with ui service", async (assert) => {
  const env = await makeTestEnv({ ...baseConfig });
  const ui = env.services.ui;
  await mount(BlockUI, { env, target });
  let blockUI = target.querySelector(".o_blockUI");
  assert.strictEqual(blockUI, null, "ui should not be blocked");
  ui.block();
  await nextTick();
  blockUI = target.querySelector(".o_blockUI");
  assert.notStrictEqual(blockUI, null, "ui should be blocked");
  ui.unblock();
  await nextTick();
  blockUI = target.querySelector(".o_blockUI");
  assert.strictEqual(blockUI, null, "ui should not be blocked");
});

QUnit.test("use block and unblock several times to block ui with ui service", async (assert) => {
  const env = await makeTestEnv({ ...baseConfig });
  const ui = env.services.ui;
  await mount(BlockUI, { env, target });
  let blockUI = target.querySelector(".o_blockUI");
  assert.strictEqual(blockUI, null, "ui should not be blocked");
  ui.block();
  ui.block();
  ui.block();
  await nextTick();
  blockUI = target.querySelector(".o_blockUI");
  assert.notStrictEqual(blockUI, null, "ui should be blocked");
  ui.unblock();
  ui.unblock();
  await nextTick();
  blockUI = target.querySelector(".o_blockUI");
  assert.notStrictEqual(blockUI, null, "ui should be blocked");
  ui.unblock();
  await nextTick();
  blockUI = target.querySelector(".o_blockUI");
  assert.strictEqual(blockUI, null, "ui should not be blocked");
});

QUnit.test("a component can be the active element", async (assert) => {
  class MyComponent extends Component {
    setup() {
      useActiveElement();
    }
  }
  MyComponent.template = owl.tags.xml`<div/>`;

  const env = await makeTestEnv({ ...baseConfig });
  const ui = env.services.ui;
  assert.deepEqual(ui.activeElement, document);

  const comp = await mount(MyComponent, { env, target });
  assert.deepEqual(ui.activeElement, comp.el);

  comp.unmount();
  assert.deepEqual(ui.activeElement, document);
  comp.destroy();
});

QUnit.test("a component can be the  UI active element: with t-ref delegation", async (assert) => {
  class MyComponent extends Component {
    setup() {
      useActiveElement("delegatedRef");
    }
  }
  MyComponent.template = owl.tags.xml`
    <div>
      <h1>My Component</h1>
      <div id="owner" t-ref="delegatedRef"/>
    </div>
  `;

  const env = await makeTestEnv({ ...baseConfig });
  const ui = env.services.ui;
  assert.deepEqual(ui.activeElement, document);

  const comp = await mount(MyComponent, { env, target });
  assert.deepEqual(ui.activeElement, comp.el.querySelector("div#owner"));

  comp.unmount();
  assert.deepEqual(ui.activeElement, document);
  comp.destroy();
});
