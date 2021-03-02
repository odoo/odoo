/** @odoo-module **/
import { uiService } from "../../src/services/ui_service";
import { Registry } from "../../src/core/registry";
import { getFixture, makeTestEnv, mount, nextTick } from "../helpers/index";
import { BlockUI } from "../../src/webclient/block_ui/block_ui";

let target;
let serviceRegistry;
let browser;
let baseConfig;
QUnit.module("UI", {
  async beforeEach() {
    target = getFixture();
    serviceRegistry = new Registry();
    serviceRegistry.add(uiService.name, uiService);
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
