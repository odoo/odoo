/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { getFixture, mount, nextTick } from "../helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

let target;
let browser;
let baseConfig;
let BlockUI, props;

QUnit.module("UI service", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("localization", makeFakeLocalizationService());
        browser = { setTimeout: () => 1 };
        baseConfig = { browser };
    },
});

QUnit.test("block and unblock once ui with ui service", async (assert) => {
    const env = await makeTestEnv({ ...baseConfig });
    ({ Component: BlockUI, props } = registry.category("main_components").get("BlockUI"));
    const ui = env.services.ui;
    await mount(BlockUI, target, { env, props });
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
    ({ Component: BlockUI, props } = registry.category("main_components").get("BlockUI"));
    const ui = env.services.ui;
    await mount(BlockUI, target, { env, props });
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

QUnit.test("a component can be the  UI active element: with t-ref delegation", async (assert) => {
    class MyComponent extends Component {
        setup() {
            useActiveElement("delegatedRef");
            this.hasRef = true;
        }
    }
    MyComponent.template = xml`
    <div>
      <h1>My Component</h1>
      <div t-if="hasRef" id="owner" t-ref="delegatedRef"/>
    </div>
  `;

    const env = await makeTestEnv({ ...baseConfig });
    const ui = env.services.ui;
    assert.deepEqual(ui.activeElement, document);

    const comp = await mount(MyComponent, target, { env });
    assert.deepEqual(ui.activeElement, document.getElementById("owner"));
    comp.hasRef = false;
    comp.render();
    await nextTick();

    assert.deepEqual(ui.activeElement, document);
});
