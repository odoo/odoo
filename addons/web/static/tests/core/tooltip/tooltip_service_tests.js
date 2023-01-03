/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { PopoverContainer } from "@web/core/popover/popover_container";
import { popoverService } from "@web/core/popover/popover_service";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { getFixture, nextTick, patchWithCleanup, triggerEvent } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";
import { makeFakeLocalizationService } from "../../helpers/mock_services";
import { templates } from "@web/core/assets";

import { App, Component, useState, xml } from "@odoo/owl";

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
 * @param {function} [options.onPopoverAdded] use this callback to check what is being passed to the popover service
 * @param {Object} [options.extraEnv] an object whose keys should be added to the env
 * @param {{[templateName:string]: string}} [options.templates] additional templates
 * @returns {Promise<Component>}
 */
export async function makeParent(Child, options = {}) {
    const target = getFixture();

    // add the popover service to the registry -> will add the PopoverContainer
    // to the mainComponentRegistry
    clearRegistryWithCleanup(mainComponents);

    patchWithCleanup(browser, {
        setTimeout: options.mockSetTimeout || ((fn) => fn()),
        clearTimeout: options.mockClearTimeout || (() => {}),
        setInterval: options.mockSetInterval || ((fn) => fn()),
        clearInterval: options.mockClearInterval || (() => {}),
        ontouchstart: options.mockOnTouchStart || undefined,
    });

    registry.category("services").add("popover", popoverService);
    registry.category("services").add("tooltip", tooltipService);
    registry.category("services").add("localization", makeFakeLocalizationService());
    let env = await makeTestEnv();
    if (options.extraEnv) {
        env = Object.create(env, Object.getOwnPropertyDescriptors(options.extraEnv));
    }

    patchWithCleanup(env.services.popover, {
        add(...args) {
            const result = this._super(...args);
            if (options.onPopoverAdded) {
                options.onPopoverAdded(...args);
            }
            return result;
        },
    });

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
        templates,
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
        await makeParent(MyComponent, { mockSetTimeout, mockSetInterval });

        assert.containsNone(target, ".o_popover_container .o_popover");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
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
        assert.containsOnce(target, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
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
        await makeParent(MyComponent, { mockSetTimeout, mockSetInterval });

        assert.containsNone(target, ".o_popover_container .o_popover");
        const [outerSpan, innerSpan] = target.querySelectorAll("span.our_span");
        outerSpan.dispatchEvent(new Event("mouseenter"));
        innerSpan.dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
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
        assert.containsOnce(target, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
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
        await makeParent(MyComponent, { mockSetInterval });

        assert.containsOnce(target, "button");
        assert.containsNone(target, ".o_popover_container .o_popover");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");

        compState.visible = false;
        await nextTick();
        assert.containsNone(target, "button");
        simulateInterval();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
    });

    QUnit.test("rendering with several tooltips", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <div>
                <button class="button_1" data-tooltip="tooltip 1">Action 1</button>
                <button class="button_2" data-tooltip="tooltip 2">Action 2</button>
            </div>`;
        await makeParent(MyComponent);

        assert.containsNone(target, ".o_popover_container .o_popover");
        target.querySelector("button.button_1").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "tooltip 1");
        target.querySelector("button.button_1").dispatchEvent(new Event("mouseleave"));
        target.querySelector("button.button_2").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "tooltip 2");
    });

    QUnit.test("positioning", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <div style="height: 400px; padding: 40px">
                <button class="default" data-tooltip="default">Default</button>
                <button class="top" data-tooltip="top" data-tooltip-position="top">Top</button>
                <button class="right" data-tooltip="right" data-tooltip-position="right">Right</button>
                <button class="bottom" data-tooltip="bottom" data-tooltip-position="bottom">Bottom</button>
                <button class="left" data-tooltip="left" data-tooltip-position="left">Left</button>
            </div>`;
        await makeParent(MyComponent, {
            onPopoverAdded(...args) {
                const { position } = args[3];
                if (position) {
                    assert.step(`popover added with position: ${position}`);
                } else {
                    assert.step(`popover added with default positioning`);
                }
            },
        });

        // default
        target.querySelector("button.default").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "default");
        assert.verifySteps(["popover added with default positioning"]);

        // top
        target.querySelector("button.top").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "top");
        assert.verifySteps(["popover added with position: top"]);

        // right
        target.querySelector("button.right").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "right");
        assert.verifySteps(["popover added with position: right"]);

        // bottom
        target.querySelector("button.bottom").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "bottom");
        assert.verifySteps(["popover added with position: bottom"]);

        // left
        target.querySelector("button.left").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(target.querySelector(".o_popover").innerText, "left");
        assert.verifySteps(["popover added with position: left"]);
    });

    QUnit.test("tooltip with a template, no info", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`
            <button data-tooltip-template="my_tooltip_template">Action</button>
        `;

        const templates = {
            my_tooltip_template: "<i t-esc='env.tooltip_text'/>",
        };
        await makeParent(MyComponent, { templates, extraEnv: { tooltip_text: "tooltip" } });

        assert.containsNone(target, ".o_popover_container .o-tooltip");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o-tooltip");
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
                    <li>X: <t t-esc="x"/></li>
                    <li>Y: <t t-esc="y"/></li>
                </ul>
            `,
        };
        await makeParent(MyComponent, { templates });

        assert.containsNone(target, ".o_popover_container .o-tooltip");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o-tooltip");
        assert.strictEqual(
            target.querySelector(".o-tooltip").innerHTML,
            "<ul><li>X: 3</li><li>Y: abc</li></ul>"
        );
    });

    QUnit.test("empty tooltip, no template", async (assert) => {
        class MyComponent extends Component {
            get tooltip() {
                return "";
            }
        }
        MyComponent.template = xml`<button t-att-data-tooltip="tooltip">Action</button>`;
        let simulateTimeout = () => {};
        const mockSetTimeout = (fn) => {
            simulateTimeout = fn;
        };
        await makeParent(MyComponent, { mockSetTimeout });

        assert.containsNone(target, ".o_popover_container .o_popover");
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        simulateTimeout();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
    });

    QUnit.test("tooltip with a delay", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`<button data-tooltip="'helpful tooltip'" data-tooltip-delay="2000">Action</button>`;
        const mockSetTimeout = (fn, delay) => {
            assert.strictEqual(delay, 2000);
        };
        await makeParent(MyComponent, { mockSetTimeout });
        target.querySelector("button").dispatchEvent(new Event("mouseenter"));
        await nextTick();
    });

    QUnit.test("touch rendering - hold-to-show", async (assert) => {
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
        const mockOnTouchStart = () => {};
        await makeParent(MyComponent, { mockSetTimeout, mockSetInterval, mockOnTouchStart });

        assert.containsNone(target, ".o_popover_container .o_popover");
        await triggerEvent(target, "button", "touchstart");
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(
            target.querySelector(".o_popover_container .o_popover").innerText,
            "hello"
        );

        await triggerEvent(target, "button", "touchend");
        assert.containsOnce(target, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
    });

    QUnit.test("touch rendering - tap-to-show", async (assert) => {
        class MyComponent extends Component {}
        MyComponent.template = xml`<button data-tooltip="hello" data-tooltip-touch-tap-to-show="true">Action</button>`;
        let simulateTimeout;
        const mockSetTimeout = (fn) => {
            simulateTimeout = fn;
        };
        let simulateInterval;
        const mockSetInterval = (fn) => {
            simulateInterval = fn;
        };
        const mockOnTouchStart = () => {};
        await makeParent(MyComponent, { mockSetTimeout, mockSetInterval, mockOnTouchStart });

        assert.containsNone(target, ".o_popover_container .o_popover");
        await triggerEvent(target, "button[data-tooltip]", "touchstart");
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(
            target.querySelector(".o_popover_container .o_popover").innerText,
            "hello"
        );

        await triggerEvent(target, "button[data-tooltip]", "touchend");
        assert.containsOnce(target, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");

        await triggerEvent(target, "button[data-tooltip]", "touchstart");
        assert.containsNone(target, ".o_popover_container .o_popover");
    });
});
