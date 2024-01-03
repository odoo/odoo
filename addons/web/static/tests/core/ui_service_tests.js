/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import { useAutofocus } from "@web/core/utils/hooks";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { getFixture, mount, nextTick, triggerEvent } from "../helpers/utils";

import { Component, useState, xml } from "@odoo/owl";
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

QUnit.test("a component can be the  UI active element: simple usage", async (assert) => {
    class MyComponent extends Component {
        setup() {
            useActiveElement("delegatedRef");
            this.hasRef = true;
        }
    }
    MyComponent.template = xml`
    <div>
      <h1>My Component</h1>
      <div t-if="hasRef" id="owner" t-ref="delegatedRef">
        <input type="text"/>
      </div>
    </div>
  `;

    const env = await makeTestEnv({ ...baseConfig });
    const ui = env.services.ui;
    assert.deepEqual(ui.activeElement, document);

    const comp = await mount(MyComponent, target, { env });
    const input = target.querySelector("#owner input");
    assert.deepEqual(ui.activeElement, document.getElementById("owner"));
    assert.strictEqual(document.activeElement, input);
    comp.hasRef = false;
    comp.render();
    await nextTick();

    assert.deepEqual(ui.activeElement, document);
    assert.strictEqual(document.activeElement, document.body);
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
    let event = await triggerEvent(document.activeElement, null, "keydown", { key: "Tab" });
    assert.strictEqual(event.defaultPrevented, true);
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withFocus]")
    );

    // Pressing 'Shift + Tab'
    event = await triggerEvent(document.activeElement, null, "keydown", {
        key: "Tab",
        shiftKey: true,
    });
    assert.strictEqual(event.defaultPrevented, true);
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
    let event = await triggerEvent(document.activeElement, null, "keydown", { key: "Tab" });
    assert.strictEqual(event.defaultPrevented, true);
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withoutFocus]")
    );

    // Pressing 'Shift + Tab'
    event = await triggerEvent(document.activeElement, null, "keydown", {
        key: "Tab",
        shiftKey: true,
    });
    assert.strictEqual(event.defaultPrevented, true);
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[placeholder=withAutoFocus]")
    );

    // Pressing 'Shift + Tab' (default)
    event = await triggerEvent(document.activeElement, null, "keydown", {
        key: "Tab",
        shiftKey: true,
    });
    assert.strictEqual(event.defaultPrevented, false);
});

QUnit.test("do not become UI active element if no element to focus", async (assert) => {
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
    assert.strictEqual(env.services.ui.activeElement, document);
});

QUnit.test("UI active element: trap focus - first or last tabable changes", async (assert) => {
    class MyComponent extends Component {
        setup() {
            this.show = useState({ a: true, c: false });
            useActiveElement("delegatedRef");
        }
    }
    MyComponent.template = xml`
        <div>
            <h1>My Component</h1>
            <input type="text" name="outer"/>
            <div id="idActiveElement" t-ref="delegatedRef">
                <div>
                    <input type="text" name="a" t-if="show.a"/>
                    <input type="text" name="b"/>
                    <input type="text" name="c" t-if="show.c"/>
                </div>
            </div>
        </div>
    `;

    const env = await makeTestEnv({ ...baseConfig });
    const comp = await mount(MyComponent, target, { env });

    assert.strictEqual(document.activeElement, target.querySelector("input[name=a]"));
    // Pressing 'Shift + Tab'
    let event = await triggerEvent(document.activeElement, null, "keydown", {
        key: "Tab",
        shiftKey: true,
    });
    assert.strictEqual(event.defaultPrevented, true);
    assert.strictEqual(document.activeElement, target.querySelector("input[name=b]"));

    comp.show.a = false;
    comp.show.c = true;
    await nextTick();
    assert.strictEqual(document.activeElement, target.querySelector("input[name=b]"));

    // Pressing 'Shift + Tab'
    event = await triggerEvent(document.activeElement, null, "keydown", {
        key: "Tab",
        shiftKey: true,
    });
    assert.strictEqual(event.defaultPrevented, true);
    assert.strictEqual(document.activeElement, target.querySelector("input[name=c]"));
});

QUnit.test(
    "UI active element: trap focus is not bypassed using invisible elements",
    async (assert) => {
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
                <input class="d-none" type="text" placeholder="withFocusNotDisplayed"/>
                <div class="d-none">
                    <input type="text" placeholder="withFocusNotDisplayedToo"/>
                </div>
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
        let event = await triggerEvent(
            document.activeElement,
            null,
            "keydown",
            { key: "Tab" },
            { fast: true }
        );

        // No other visible element is found
        assert.strictEqual(event.defaultPrevented, true);
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("input[placeholder=withFocus]")
        );

        // Pressing 'Shift + Tab'
        event = await triggerEvent(
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
    }
);
