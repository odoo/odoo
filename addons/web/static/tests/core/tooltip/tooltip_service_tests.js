/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { PopoverContainer } from "@web/core/popover/popover_container";
import { popoverService } from "@web/core/popover/popover_service";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { getFixture, nextTick, patchWithCleanup, triggerEvent } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";

const { App, Component, useState, xml } = owl;

const mainComponents = registry.category("main_components");

/**
 * Creates and mounts a parent component that use the "useTooltip" hook.
 *
 * @param {Component} Child a child Component that contains nodes with "data-tooltip" attribute
 * @param {Object} [options]
 * @param {function} [options.mockSetTimeout] the mocked setTimeout to use (by default, calls the
 *   callback directly)
 * @param {function} [options.mockSetInterval] the mocked setInterval to use (by default, calls the
 *   callback directly)
 * @param {function} [options.mockClearTimeout] the mocked clearTimeout to use (by default, does nothing)
 * @param {function} [options.mockClearInterval] the mocked clearInterval to use (by default, does nothing)
 * @param {{[templateName:string]: string}} [options.templates] additional templates
 * @returns {Promise<Component>}
 */
async function makeParent(Child, options = {}) {
    const target = getFixture();

    // add the popover service to the registry -> will add the PopoverContainer
    // to the mainComponentRegistry
    clearRegistryWithCleanup(mainComponents);

    patchWithCleanup(browser, {
        setTimeout: options.mockSetTimeout || ((fn) => fn()),
        clearTimeout: options.mockClearTimeout || (() => {}),
        setInterval: options.mockSetInterval || ((fn) => fn()),
        clearInterval: options.mockClearInterval || (() => {}),
    });

    registry.category("services").add("popover", popoverService);
    registry.category("services").add("tooltip", tooltipService);
    const env = await makeTestEnv();

    class Parent extends Component {
        setup() {
            this.Components = mainComponents.getEntries();
        }
    }
    Parent.template = xml`
        <div>
            <Child/>
            <div>
                <t t-foreach="Components" t-as="Component" t-key="Component[0]">
                    <t t-component="Component[1].Component" t-props="Component[1].props"/>
                </t>
            </div>
        </div>`;
    Parent.components = { PopoverContainer, Child };

    const app = new App(Parent, {
        env,
        target,
        templates: window.__OWL_TEMPLATES__,
        test: true,
    });
    registerCleanup(() => app.destroy());
    for (const [name, template] of Object.entries(options.templates || {})) {
        app.addTemplate(name, template);
    }

    return app.mount(target);
}

let target;
QUnit.module("Tooltip service", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
    });

    QUnit.test("basic rendering", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`<button data-tooltip="hello">Action</button>`;
        let simulateTimeout;
        const mockSetTimeout = (fn) => {
            simulateTimeout = fn;
        };
        let simulateInterval;
        const mockSetInterval = (fn) => {
            simulateInterval = fn;
        };
        const parent = await makeParent(MyComponent, { mockSetTimeout, mockSetInterval });

        assert.containsNone(parent, ".o_popover_container .o_popover");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsNone(parent, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(
            target.querySelector(".o_popover_container .o_popover").innerText,
            "hello"
        );

        const buttonRect = target.querySelector("button").getBoundingClientRect();
        const x = buttonRect.right + 10;
        const y = buttonRect.bottom + 10;
        await triggerEvent(target, "button", "mousemove", {
            pageX: x,
            layerX: x,
            screenX: x,
            pageY: y,
            layerY: y,
            screenY: y,
        });
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(parent, ".o_popover_container .o_popover");
    });

    QUnit.test("basic rendering 2", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`<span data-tooltip="hello" class="our_span"><span class="our_span">Action</span></span>`;
        let simulateTimeout;
        const mockSetTimeout = (fn) => {
            simulateTimeout = fn;
        };
        let simulateInterval;
        const mockSetInterval = (fn) => {
            simulateInterval = fn;
        };
        const parent = await makeParent(MyComponent, { mockSetTimeout, mockSetInterval });

        assert.containsNone(parent, ".o_popover_container .o_popover");
        let [outerSpan, innerSpan] = target.querySelectorAll("span.our_span");
        outerSpan.dispatchEvent(new Event("mouseenter"));
        innerSpan.dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsNone(parent, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(
            target.querySelector(".o_popover_container .o_popover").innerText,
            "hello"
        );

        const outerSpanRect = outerSpan.getBoundingClientRect();
        const x = outerSpanRect.right + 10;
        const y = outerSpanRect.bottom + 10;
        await triggerEvent(target, 'span[data-tooltip="hello"]', "mousemove", {
            pageX: x,
            layerX: x,
            screenX: x,
            pageY: y,
            layerY: y,
            screenY: y,
        });
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(parent, ".o_popover_container .o_popover");
    });

    QUnit.test("remove element with opened tooltip", async (assert) => {
        let compState;
        class MyComponent extends Component {
            setup() {
                this.state = useState({ visible: true });
                compState = this.state;
            }
        }
        MyComponent.template = xml`
            <div>
                <button t-if="state.visible" data-tooltip="hello">Action</button>
            </div>`;
        let simulateInterval;
        const mockSetInterval = (fn) => {
            simulateInterval = fn;
        };
        const parent = await makeParent(MyComponent, { mockSetInterval });

        assert.containsOnce(parent, "button");
        assert.containsNone(parent, ".o_popover_container .o_popover");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");

        compState.visible = false;
        await nextTick();
        assert.containsNone(parent, "button");
        simulateInterval();
        await nextTick();
        assert.containsNone(parent, ".o_popover_container .o_popover");
    });

    QUnit.test("rendering with several tooltips", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <div>
                <button class="button_1" data-tooltip="tooltip 1">Action 1</button>
                <button class="button_2" data-tooltip="tooltip 2">Action 2</button>
            </div>`;
        const parent = await makeParent(MyComponent);

        assert.containsNone(parent, ".o_popover_container .o_popover");
        target.querySelector("button.button_1").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "tooltip 1");
        target.querySelector("button.button_1").dispatchEvent(new Event("mouseleave"));
        target.querySelector("button.button_2").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "tooltip 2");
    });

    QUnit.test("positionning", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <div style="height: 400px; padding: 40px">
                <button class="default" data-tooltip="default">Default</button>
                <button class="top" data-tooltip="top" data-tooltip-position="top">Top</button>
                <button class="right" data-tooltip="right" data-tooltip-position="right">Right</button>
                <button class="bottom" data-tooltip="bottom" data-tooltip-position="bottom">Bottom</button>
                <button class="left" data-tooltip="left" data-tooltip-position="left">Left</button>
            </div>`;
        const parent = await makeParent(MyComponent);

        // default
        target.querySelector("button.default").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "default");
        assert.hasClass(target.querySelector(".o_popover"), "o-popper-position--bm");

        // top
        target.querySelector("button.top").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "top");
        assert.hasClass(target.querySelector(".o_popover"), "o-popper-position--tm");

        // right
        target.querySelector("button.right").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "right");
        assert.hasClass(target.querySelector(".o_popover"), "o-popper-position--rm");

        // bottom
        target.querySelector("button.bottom").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "bottom");
        assert.hasClass(target.querySelector(".o_popover"), "o-popper-position--bm");

        // left
        target.querySelector("button.left").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "left");
        assert.hasClass(target.querySelector(".o_popover"), "o-popper-position--lm");
    });

    QUnit.test("tooltip with a template, no info", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <button data-tooltip-template="my_tooltip_template">Action</button>
        `;

        const templates = {
            my_tooltip_template: "<i>tooltip</i>",
        };
        const parent = await makeParent(MyComponent, { templates });

        assert.containsNone(parent, ".o_popover_container .o-tooltip");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o-tooltip");
        assert.strictEqual(target.querySelector(".o-tooltip").innerHTML, "<i>tooltip</i>");
    });

    QUnit.test("tooltip with a template and info", async (assert) => {
        class MyComponent extends Component {
            get info() {
                return JSON.stringify({ x: 3, y: "abc" });
            }
        }
        MyComponent.template = xml`
            <button
                data-tooltip-template="my_tooltip_template"
                t-att-data-tooltip-info="info">
                Action
            </button>
        `;

        const templates = {
            my_tooltip_template: `
                <ul>
                    <li>X: <t t-esc="info.x"/></li>
                    <li>Y: <t t-esc="info.y"/></li>
                </ul>
            `,
        };
        const parent = await makeParent(MyComponent, { templates });

        assert.containsNone(parent, ".o_popover_container .o-tooltip");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(parent, ".o_popover_container .o-tooltip");
        assert.strictEqual(
            target.querySelector(".o-tooltip").innerHTML,
            "<ul><li>X: 3</li><li>Y: abc</li></ul>"
        );
    });
});
