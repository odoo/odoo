// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    click,
    drag,
    hover,
    leave,
    pointerDown,
    pointerUp,
    press,
    queryOne,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { getDetachedTargetObserverCount } from "@web/ui/popover/detached_target_watcher";
import { popoverService } from "@web/ui/popover/popover_service";
import { OPEN_DELAY, SHOW_AFTER_DELAY } from "@web/ui/tooltip/tooltip_service";

test("tooltip cleanup preserves title and descriptions updated by the owner", async () => {
    class Content extends Component {
        static template = xml`<button data-tooltip="help" title="old" aria-describedby="original">target</button>`;
        static props = {};
    }
    await mountWithCleanup(Content);
    const target = queryOne("[data-tooltip]");
    target.focus();
    await runAllTimers();
    const id = queryOne(".o-tooltip").id;
    target.setAttribute("title", "new title");
    target.setAttribute("aria-describedby", `updated ${id} additional`);
    getService("tooltip").cleanup();
    expect(target).toHaveAttribute("title", "new title");
    expect(target).toHaveAttribute("aria-describedby", "updated additional");
});

test("tooltip cleanup does not resurrect a description removed by the owner", async () => {
    class Content extends Component {
        static template = xml`<button data-tooltip="help" aria-describedby="original">target</button>`;
        static props = {};
    }
    await mountWithCleanup(Content);
    const target = queryOne("[data-tooltip]");
    target.focus();
    await runAllTimers();
    target.removeAttribute("aria-describedby");
    getService("tooltip").cleanup();
    expect(target).not.toHaveAttribute("aria-describedby");
});

test("moving keyboard focus inside a tooltip wrapper preserves its description", async () => {
    class Content extends Component {
        static props = ["*"];
        static template = xml`<span data-tooltip="help"><button class="first">first</button><button class="second">second</button></span>`;
    }
    await mountWithCleanup(Content);
    queryOne(".first").focus();
    await runAllTimers();
    const id = queryOne(".o-tooltip").id;
    queryOne(".second").focus();
    await animationFrame();
    expect(".o-tooltip").toHaveCount(1);
    expect(".o-tooltip").toHaveAttribute("id", id);
    expect("[data-tooltip]").toHaveAttribute("aria-describedby", id);
});

test("a tooltip on a wrapper closes when keyboard focus leaves its child", async () => {
    class Content extends Component {
        static props = ["*"];
        static template = xml`<div><span data-tooltip="help"><button class="inside">inside</button></span><button class="outside">outside</button></div>`;
    }
    await mountWithCleanup(Content);
    queryOne(".inside").focus();
    await runAllTimers();
    expect(".o-tooltip").toHaveCount(1);
    queryOne(".outside").focus();
    await animationFrame();
    expect(".o-tooltip").toHaveCount(0);
});

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
    /** @type {{ visible: boolean; }} */
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
    await animationFrame();
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
        patchWithCleanup(popover, {
            add(...args) {
                const { position } = args[3];
                if (position) {
                    expect.step(`popover added with position: ${position}`);
                } else {
                    expect.step(`popover added with default positioning`);
                }
                return super.add(...args);
            },
        });
        return popover;
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

    await hover("button.default");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("default");
    expect.verifySteps(["popover added with default positioning"]);

    await hover("button.top");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("top");
    expect.verifySteps(["popover added with position: top"]);

    await hover("button.right");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("right");
    expect.verifySteps(["popover added with position: right"]);

    await hover("button.bottom");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveText("bottom");
    expect.verifySteps(["popover added with position: bottom"]);

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
            my_tooltip_template: `<i t-esc='env.tooltip_text'/>`,
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
            my_tooltip_template: `
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

    queryOne(".mybtn").remove();

    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("a tooltip watches its target without polling, and releases it", async () => {
    const intervals = [];
    patchWithCleanup(browser, {
        setInterval(fn, delay) {
            intervals.push(delay);
            return super.setInterval(fn, delay);
        },
    });

    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    expect(getDetachedTargetObserverCount()).toBe(0);

    await hover(".mybtn");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(intervals).toEqual([]);
    expect(getDetachedTargetObserverCount()).toBe(1);

    await press("Escape");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
    expect(intervals).toEqual([]);
    expect(getDetachedTargetObserverCount()).toBe(0);
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

    await click("button[data-tooltip]");
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    await pointerDown("button[data-tooltip]");
    await advanceTime(SHOW_AFTER_DELAY);
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);

    await pointerDown(document.body);
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("a custom tooltip suppresses the native title, then restores it", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" title="native help" data-tooltip="custom">Action</button>`;
    }
    await mountWithCleanup(MyComponent);

    await hover(".mybtn");
    await advanceTime(OPEN_DELAY);
    await animationFrame();
    expect(".o-tooltip").toHaveCount(1);

    await hover(document.body);
    await advanceTime(OPEN_DELAY * 3);
    await animationFrame();

    expect(document.querySelector(".mybtn").getAttribute("title")).toBe("native help");
});

const bareClick = (/** @type {string} */ selector) =>
    queryOne(selector).dispatchEvent(new MouseEvent("click", { bubbles: true }));

test.tags("desktop");
test("clicking a child of the tooltipped element cancels the pending tooltip", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello"><span class="inner">Action</span></button>`;
    }

    await mountWithCleanup(MyComponent);
    await hover(".inner");
    await click(".inner");
    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
});

test.tags("mobile");
test("a tap-to-show tooltip survives the click that ends the tap", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello" data-tooltip-touch-tap-to-show="true"><span class="inner">Action</span></button>`;
    }

    await mountWithCleanup(MyComponent);
    await pointerDown(".inner");
    await advanceTime(SHOW_AFTER_DELAY);
    expect(".o_popover").toHaveCount(0);

    await pointerUp(".inner");
    bareClick(".inner");
    await advanceTime(OPEN_DELAY);
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
});

test.tags("mobile");
test("a hold-to-show tooltip is still cancelled by the click that ends the tap", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello"><span class="inner">Action</span></button>`;
    }

    await mountWithCleanup(MyComponent);
    await pointerDown(".inner");
    await advanceTime(SHOW_AFTER_DELAY);
    await pointerUp(".inner");
    bareClick(".inner");
    await advanceTime(OPEN_DELAY * 3);
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("a custom tooltip is exposed to assistive technology", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" title="native help" data-tooltip="custom help">Action</button>`;
    }
    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");

    await hover(".mybtn");
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(1);

    const tooltip = queryOne(".o-tooltip");
    expect(tooltip).toHaveAttribute("role", "tooltip");
    expect(tooltip.id).not.toBe("");
    expect(btn).toHaveAttribute("aria-describedby", tooltip.id);
    expect(btn).not.toHaveAttribute("title");

    await leave();
    await advanceTime(OPEN_DELAY);
    expect(".o_popover").toHaveCount(0);
    expect(btn).toHaveAttribute("title", "native help");
    expect(btn).not.toHaveAttribute("aria-describedby");
});

test.tags("desktop");
test("a tooltip keeps a description the element already had", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <div>
                <button class="mybtn" aria-describedby="field_help" data-tooltip="custom help">Action</button>
                <span id="field_help">the field help</span>
            </div>`;
    }
    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");

    await hover(".mybtn");
    await advanceTime(OPEN_DELAY);
    const tooltip = queryOne(".o-tooltip");
    expect(btn).toHaveAttribute("aria-describedby", `field_help ${tooltip.id}`);

    await leave();
    await advanceTime(OPEN_DELAY);
    expect(btn).toHaveAttribute("aria-describedby", "field_help");
});

test.tags("desktop");
test("clicking a child of the tooltipped element closes an OPEN tooltip", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" data-tooltip="hello"><span class="inner">Action</span></button>`;
    }

    await mountWithCleanup(MyComponent);
    await hover(".inner");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    await click(".inner");
    await runAllTimers();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("tooltip info built from a t-set body survives the JSON round-trip", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <t t-set="body">on their friends' or followers' feed (Shares, Reposts...)</t>
            <button
                data-tooltip-template="my_tooltip_template"
                t-att-data-tooltip-info="toJsonString({ title: 'Stories', content: body })">
                Action
            </button>
        `;
        toJsonString(obj) {
            return JSON.stringify(obj);
        }
    }

    await mountWithCleanup(MyComponent, {
        templates: {
            my_tooltip_template: `
                <div><b t-esc="title"/><span t-esc="content"/></div>
            `,
        },
    });

    expect(() =>
        JSON.parse(queryOne("button").getAttribute("data-tooltip-info")),
    ).not.toThrow();

    await hover("button");
    await runAllTimers();

    expect(".o-tooltip b").toHaveText("Stories");
    expect(".o-tooltip span").toHaveText(
        "on their friends' or followers' feed (Shares, Reposts...)",
    );
});

test.tags("mobile");
test("a touch cancelled before the tooltip opens restores the native title", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" title="native help" data-tooltip="custom help">Action</button>`;
    }

    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");
    const observersBefore = getDetachedTargetObserverCount();

    await pointerDown(".mybtn");
    await advanceTime(SHOW_AFTER_DELAY);
    expect(btn).not.toHaveAttribute("title");
    expect(".o_popover").toHaveCount(0);

    btn.dispatchEvent(new TouchEvent("touchcancel", { bubbles: true }));
    await animationFrame();
    expect(btn).toHaveAttribute("title", "native help");
    expect(getDetachedTargetObserverCount()).toBe(observersBefore);

    await runAllTimers();
    expect(".o_popover").toHaveCount(0);
    expect(btn).toHaveAttribute("title", "native help");
});

test.tags("desktop");
test("destroying the service restores what an open tooltip borrowed", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn" title="native tip" data-tooltip="rich tip">Action</button>`;
    }
    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");

    await hover(".mybtn");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(btn).not.toHaveAttribute("title");
    expect(btn).toHaveAttribute("aria-describedby");

    getService("tooltip").destroy();
    await animationFrame();

    expect(btn).toHaveAttribute("title", "native tip");
    expect(btn).not.toHaveAttribute("aria-describedby");
    expect(".o_popover").toHaveCount(0);
});

test.tags("desktop");
test("a service-registered tooltip survives a repeated mouseenter", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn">Action</button>`;
    }
    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");
    getService("tooltip").add(btn, { tooltip: "hello" });

    await hover(".mybtn");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    btn.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false }));
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
});

test.tags("desktop");
test("a service-registered tooltip survives the target taking focus", async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<button class="mybtn">Action</button>`;
    }
    await mountWithCleanup(MyComponent);
    const btn = queryOne(".mybtn");
    getService("tooltip").add(btn, { tooltip: "hello" });

    await hover(".mybtn");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);

    btn.focus();
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
});

test.tags("desktop");
test("a malformed tooltip delay falls back to the default", async () => {
    class Host extends Component {
        static template = xml`<button class="t" data-tooltip="hi" data-tooltip-delay="abc">b</button>`;
        static props = ["*"];
    }
    await mountWithCleanup(Host);
    await hover(".t");

    await advanceTime(50);
    await animationFrame();
    expect(".o-tooltip").toHaveCount(0);

    await advanceTime(OPEN_DELAY);
    await animationFrame();
    expect(".o-tooltip").toHaveCount(1);
});

test.tags("desktop");
test("a negative tooltip delay falls back to the default too", async () => {
    class Host extends Component {
        static template = xml`<button class="t" data-tooltip="hi" data-tooltip-delay="-500">b</button>`;
        static props = ["*"];
    }
    await mountWithCleanup(Host);
    await hover(".t");

    await advanceTime(50);
    await animationFrame();
    expect(".o-tooltip").toHaveCount(0);

    await advanceTime(OPEN_DELAY);
    await animationFrame();
    expect(".o-tooltip").toHaveCount(1);
});
