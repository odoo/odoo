import { expect, test } from "@odoo/hoot";
import { click, drag, hover, leave, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { Component, proxy, xml } from "@odoo/owl";
import {
    assignTestEnv,
    mountWithCleanup,
    patchWithCleanup,
    registerTemplate,
} from "@web/../tests/web_test_helpers";

import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { OPEN_DELAY, SHOW_AFTER_DELAY } from "@web/core/tooltip/tooltip_service";

test.tags("desktop");
test("basic rendering", async () => {
    class MyComponent extends Component {
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
        static template = xml`
            <div>
                <button t-if="this.state.visible" data-tooltip="hello">Action</button>
            </div>`;
        setup() {
            this.state = proxy({ visible: true });
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
    patchWithCleanup(PopoverPlugin.prototype, {
        add(target, component, props, options) {
            const { position } = options;
            if (position) {
                expect.step(`popover added with position: ${position}`);
            } else {
                expect.step(`popover added with default positioning`);
            }
            return super.add(target, component, props, options);
        },
    });

    class MyComponent extends Component {
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
        static template = xml`
            <button data-tooltip-template="my_tooltip_template">Action</button>
        `;
    }

    registerTemplate("my_tooltip_template", /* xml */ `<i t-out='env.tooltip_text'/>`);
    assignTestEnv({ tooltip_text: "tooltip" });
    await mountWithCleanup(MyComponent);

    expect(".o-tooltip").toHaveCount(0);

    await hover("button");
    await runAllTimers();

    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveInnerHTML("<i>tooltip</i>");
});

test.tags("desktop");
test("tooltip with a template and info", async () => {
    class MyComponent extends Component {
        static template = xml`
            <button
                data-tooltip-template="my_tooltip_template"
                t-att-data-tooltip-info="this.info">
                Action
            </button>
        `;
        get info() {
            return JSON.stringify({ x: 3, y: "abc" });
        }
    }

    registerTemplate(
        "my_tooltip_template",
        /* xml */ `
            <ul>
                <li>X: <t t-out="x"/></li>
                <li>Y: <t t-out="y"/></li>
            </ul>
        `
    );
    await mountWithCleanup(MyComponent);

    expect(".o-tooltip").toHaveCount(0);

    await hover("button");
    await runAllTimers();

    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveInnerHTML("<ul><li>X: 3</li><li>Y: abc</li></ul>");
});

test.tags("desktop");
test("empty tooltip, no template", async () => {
    class MyComponent extends Component {
        static template = xml`<button t-att-data-tooltip="this.tooltip">Action</button>`;
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

test.tags("desktop");
test("tooltip from and to child element", async () => {
    class MyComponent extends Component {
        static template = xml`
        <div class="no-tooltip">space</div>
        <div class="p-5" data-tooltip="hello">
            <button>Action</button>
        </div>`;
    }

    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);

    await pointerDown("div[data-tooltip]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    const popover = queryOne(".o_popover");

    await pointerDown("button");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(queryOne(".o_popover")).toBe(popover);

    await pointerDown("div[data-tooltip]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(queryOne(".o_popover")).toBe(popover);

    await pointerDown(".no-tooltip");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(0);
});

test.tags("mobile");
test("tooltip from the title attribute", async () => {
    class MyComponent extends Component {
        static template = xml`
        <div title="Coucou">
            Toto
        </div>`;
    }
    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);
    await pointerDown("div[title]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("Coucou");
});

test.tags("mobile");
test("no tooltip from the title attribute if it is the text of the element", async () => {
    class MyComponent extends Component {
        static template = xml`
        <div title="Toto" style="width: 300px">
            Toto
        </div>`;
    }
    await mountWithCleanup(MyComponent);
    expect(".o_popover").toHaveCount(0);
    await pointerDown("div[title]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(0);
});

test.tags("mobile");
test("tooltip from the title attribute if the text is truncated", async () => {
    class MyComponent extends Component {
        static template = xml`
        <div class="mytext" title="Toto is a very long text" style="width: 40px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">Toto is a very long text</div>`;
    }
    await mountWithCleanup(MyComponent);
    const textEl = queryOne(".mytext");
    expect(textEl.scrollWidth).toBeGreaterThan(textEl.clientWidth); // the text is truncated

    await pointerDown("div[title]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("Toto is a very long text");
});

test.tags("desktop");
test("no tooltip if it is the text content of the element, entirely displayed", async () => {
    class MyComponent extends Component {
        static template = xml`
            <span class="mytext" style="display: inline-block; width: 300px" data-tooltip="hello">hello</span>`;
    }

    await mountWithCleanup(MyComponent);
    const textEl = queryOne(".mytext");
    expect(textEl.scrollWidth).toBe(textEl.clientWidth); // the text isn't truncated

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("tooltip if it is the text content of the element, but truncated", async () => {
    class MyComponent extends Component {
        static template = xml`
            <span class="mytext" style="display: inline-block; width: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" data-tooltip="hello everyone">hello everyone</span>`;
    }

    await mountWithCleanup(MyComponent);
    const textEl = queryOne(".mytext");
    expect(textEl.scrollWidth).toBeGreaterThan(textEl.clientWidth); // the text is truncated

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello everyone");
});

test.tags("desktop");
test("tooltip if it isn't exactly the text content of the element", async () => {
    class MyComponent extends Component {
        static template = xml`
            <span class="mytext" style="display: inline-block; width: 300px" data-tooltip="hello everyone">hello</span>`;
    }

    await mountWithCleanup(MyComponent);

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello everyone");
});

test.tags("desktop");
test("tooltip with a template is never considered redundant", async () => {
    class MyComponent extends Component {
        static template = xml`
            <span class="mytext" style="display: inline-block; width: 300px" data-tooltip-template="my_tooltip_template">hello</span>`;
    }

    registerTemplate("my_tooltip_template", /* xml */ `<i>hello</i>`);
    await mountWithCleanup(MyComponent);

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");
});

test.tags("desktop");
test("tooltip on an element whose overflow can't be measured", async () => {
    class MyComponent extends Component {
        static template = xml`<div><span class="mytext" data-tooltip="hello">hello</span></div>`;
    }

    await mountWithCleanup(MyComponent);
    expect(queryOne(".mytext").clientWidth).toBe(0); // inline element

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello");
});

test.tags("desktop");
test("tooltip if the text content is truncated in a descendant", async () => {
    class MyComponent extends Component {
        static template = xml`
            <span class="mytext" style="display: inline-block; width: 300px" data-tooltip="hello everyone">
                <div class="inner" style="width: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">hello everyone</div>
            </span>`;
    }

    await mountWithCleanup(MyComponent);
    const textEl = queryOne(".mytext");
    const innerEl = queryOne(".inner");
    expect(textEl.scrollWidth).toBe(textEl.clientWidth); // the element itself doesn't overflow
    expect(innerEl.scrollWidth).toBeGreaterThan(innerEl.clientWidth); // but its descendant does

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("hello everyone");
});

test.tags("desktop");
test("no tooltip if the text content is entirely displayed in a descendant", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div class="mytext" style="width: 300px" data-tooltip="hello"><span class="inner">hello</span></div>`;
    }

    await mountWithCleanup(MyComponent);
    expect(queryOne(".inner").clientWidth).toBe(0); // inline descendant, can't be measured

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("no tooltip if only a descendant without text content overflows", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div class="mytext" style="display: flex; width: 300px" data-tooltip="hello">
                <button class="icon" style="width: 20px; overflow: hidden">
                    <i style="display: inline-block; width: 50px"/>
                </button>
                <span class="label">hello</span>
            </div>`;
    }

    await mountWithCleanup(MyComponent);
    const iconEl = queryOne(".icon");
    expect(iconEl.scrollWidth).toBeGreaterThan(iconEl.clientWidth); // the icon overflows
    expect(iconEl.textContent.trim()).toBe(""); // but it doesn't display any text

    await hover(".mytext");
    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});
