/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import { useAutofocus } from "@web/core/utils/hooks";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { getFixture, mount, nextTick, triggerEvent } from "../helpers/utils";

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

QUnit.test("UI active element: trap focus", async (assert) => {
    class MyComponent extends Component {
        setup() {
            useActiveElement("delegatedRef");
        }
    }
    MyComponent.template = xml`
        <div>
            <h1>My Component</h1>
            <input type="text" placeholder="outerUIActiveElement"/>
            <div t-ref="delegatedRef">
                <input type="text" placeholder="withFocus"/>
            </div>
        </div>
    `;

    const env = await makeTestEnv({ ...baseConfig });
    await mount(MyComponent, target, { env });

    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withFocus]"),
        "The focus is on the first 'focusable' element of the UI active element"
    );

    // Pressing 'Tab'
    let event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab" },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withFocus]")
    );

    // Pressing 'Shift + Tab'
    event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab", shiftKey: true },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withFocus]")
    );
});

QUnit.test("UI active element: trap focus - default focus with autofocus", async (assert) => {
    class MyComponent extends Component {
        setup() {
            useActiveElement("delegatedRef");
            useAutofocus();
        }
    }
    MyComponent.template = xml`
        <div>
            <h1>My Component</h1>
            <input type="text" placeholder="outerUIActiveElement"/>
            <div t-ref="delegatedRef">
                <input type="text" placeholder="withoutFocus"/>
                <input type="text" t-ref="autofocus" placeholder="withAutoFocus"/>
            </div>
        </div>
    `;

    const env = await makeTestEnv({ ...baseConfig });
    await mount(MyComponent, target, { env });

    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withAutoFocus]"),
        "The focus is on the autofocus element of the UI active element"
    );

    // Pressing 'Tab'
    let event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab" },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withoutFocus]")
    );

    // Pressing 'Shift + Tab'
    event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab", shiftKey: true },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withAutoFocus]")
    );

    // Pressing 'Shift + Tab' (default)
    event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab", shiftKey: true },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, false);
});

QUnit.test("UI active element: trap focus - no focus element", async (assert) => {
    class MyComponent extends Component {
        setup() {
            useActiveElement("delegatedRef");
        }
    }
    MyComponent.template = xml`
        <div>
            <h1>My Component</h1>
            <input type="text" placeholder="outerUIActiveElement"/>
            <div id="idActiveElement" t-ref="delegatedRef">
                <div>
                    <span> No focus element </span>
                </div>
            </div>
        </div>
    `;

    const env = await makeTestEnv({ ...baseConfig });
    await mount(MyComponent, target, { env });

    assert.strictEqual(
        document.activeElement,
        target.querySelector("div[id=idActiveElement]"),
        "when there is not other element, the focus is on the UI active element itself"
    );
    // Pressing 'Tab'
    let event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab" },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(document.activeElement, target.querySelector("div[id=idActiveElement]"));

    // Pressing 'Shift + Tab'
    event = triggerEvent(
        document.activeElement,
        null,
        "keydown",
        { key: "Tab", shiftKey: true },
        { fast: true }
    );
    assert.strictEqual(event.defaultPrevented, true);
    await nextTick();
    assert.strictEqual(document.activeElement, target.querySelector("div[id=idActiveElement]"));
});
