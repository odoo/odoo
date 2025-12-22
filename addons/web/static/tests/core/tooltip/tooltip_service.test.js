import { expect, test } from "@odoo/hoot";
import { click, drag, hover, leave, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { makeMockEnv, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { popoverService } from "@web/core/popover/popover_service";
import { OPEN_DELAY, SHOW_AFTER_DELAY } from "@web/core/tooltip/tooltip_service";

test.tags("desktop");
test("basic rendering", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);
    await hover(".mybtn");
    expect(".o_popover").toHaveCount(0);

    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");

    await leave();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("basic rendering 2", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<span data-tooltip="hello" class="outer_span"><span class="inner_span">Action</span></span>`;
    }

    await mountWithCleanup(MyComponent);

    expect(".o_popover").toHaveCount(0);
    await hover(".inner_span");
    expect(".o_popover").toHaveCount(0);

    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");

    await hover(".outer_span");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    await leave();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("remove element with opened tooltip", async () => {
    let compState;
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <div>
                <button t-if="state.visible" data-tooltip="hello">Action</button>
            </div>`;
        setup() {
            this.state = useState({ visible: true });
            compState = this.state;
        }
    }

    await mountWithCleanup(MyComponent);

    expect("button").toHaveCount(1);
    expect(".o_popover").toHaveCount(0);
    await hover("button");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    compState.visible = false;
    await animationFrame();
    expect("button").toHaveCount(0);
    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("rendering with several tooltips", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <div>
                <button class="button_1" data-tooltip="tooltip 1">Action 1</button>
                <button class="button_2" data-tooltip="tooltip 2">Action 2</button>
            </div>`;
    }

    await mountWithCleanup(MyComponent);

    expect(".o_popover").toHaveCount(0);

    await hover("button.button_1");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("tooltip 1");

    await hover("button.button_2");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("tooltip 2");
});

test.tags("desktop");
test("positioning", async () => {
    mockService("popover", (...kargs) => {
        const popover = popoverService.start(...kargs);
        return {
            add(...args) {
                const { position } = args[3];
                if (position) {
                    expect.step(`popover added with position: ${position}`);
                } else {
                    expect.step(`popover added with default positioning`);
                }
                return popover.add(...args);
            },
        };
    });

    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <div style="height: 400px; padding: 40px">
                <button class="default" data-tooltip="default">Default</button>
                <button class="top" data-tooltip="top" data-tooltip-position="top">Top</button>
                <button class="right" data-tooltip="right" data-tooltip-position="right">Right</button>
                <button class="bottom" data-tooltip="bottom" data-tooltip-position="bottom">Bottom</button>
                <button class="left" data-tooltip="left" data-tooltip-position="left">Left</button>
            </div>`;
    }

    await mountWithCleanup(MyComponent);

    // default
    await hover("button.default");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("default");
    expect.verifySteps(["popover added with default positioning"]);

    // top
    await hover("button.top");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("top");
    expect.verifySteps(["popover added with position: top"]);

    // right
    await hover("button.right");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("right");
    expect.verifySteps(["popover added with position: right"]);

    // bottom
    await hover("button.bottom");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("bottom");
    expect.verifySteps(["popover added with position: bottom"]);

    // left
    await hover("button.left");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("left");
    expect.verifySteps(["popover added with position: left"]);
});

test.tags("desktop");
test("tooltip with a template, no info", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <button data-tooltip-template="my_tooltip_template">Action</button>
        `;
    }

    await makeMockEnv({ tooltip_text: "tooltip" });
    await mountWithCleanup(MyComponent, {
        templates: {
            my_tooltip_template: /* xml */ `<i t-esc='env.tooltip_text'/>`,
        },
    });

    expect(".o-tooltip").toHaveCount(0);

    await hover("button");
    await runAllTimers();

    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveInnerHTML("<i>tooltip</i>");
});

test.tags("desktop");
test("tooltip with a template and info", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <button
                data-tooltip-template="my_tooltip_template"
                t-att-data-tooltip-info="info">
                Action
            </button>
        `;
        get info() {
            return JSON.stringify({ x: 3, y: "abc" });
        }
    }

    await mountWithCleanup(MyComponent, {
        templates: {
            my_tooltip_template: /* xml */ `
                <ul>
                    <li>X: <t t-esc="x"/></li>
                    <li>Y: <t t-esc="y"/></li>
                </ul>
            `,
        },
    });

    expect(".o-tooltip").toHaveCount(0);

    await hover("button");
    await runAllTimers();

    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveInnerHTML("<ul><li>X: 3</li><li>Y: abc</li></ul>");
});

test.tags("desktop");
test("empty tooltip, no template", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button t-att-data-tooltip="tooltip">Action</button>`;
        get tooltip() {
            return "";
        }
    }

    await mountWithCleanup(MyComponent);
    expect(".o-tooltip").toHaveCount(0);
    await hover("button");
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(0);
});

test.tags("desktop");
test("tooltip with a delay", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="myBtn" data-tooltip="'helpful tooltip'" data-tooltip-delay="2000">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o-tooltip").toHaveCount(0);

    await hover("button.myBtn");
    await advanceTime(OPEN_DELAY);
    expect(".o-tooltip").toHaveCount(0);
    await advanceTime(2000 - OPEN_DELAY);
    expect(".o-tooltip").toHaveCount(1);
});

test.tags("desktop");
test("tooltip does not crash with disappearing target", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);

    await hover(".mybtn");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    // the element disappeared from the DOM during the setTimeout
    queryOne(".mybtn").remove();

    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("tooltip using touch enabled device", async () => {
    mockTouch(true);

    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);

    await drag(".mybtn");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");

    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");
});

test.tags("mobile");
test("touch rendering - hold-to-show", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button data-tooltip="hello">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);
    await pointerDown("button");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");

    await pointerUp("button");
    await animationFrame();
    expect(".o_popover").toHaveCount(1);

    await pointerDown(document.body);
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("mobile");
test("touch rendering - tap-to-show", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button data-tooltip="hello" data-tooltip-touch-tap-to-show="true">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);
    await pointerDown("button[data-tooltip]");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");

    await pointerUp("button");
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    // The tooltip should be closed if you click on the button itself
    await click("button[data-tooltip]");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    // Reopen it
    await pointerDown("button[data-tooltip]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);

    // The tooltip should be also closed if you click anywhere else
    await pointerDown(document.body);
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});
