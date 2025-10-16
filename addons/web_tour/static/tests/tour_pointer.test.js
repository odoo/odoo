/** @odoo-module **/

import { advanceTime, after, beforeEach, describe, expect, test } from "@odoo/hoot";
import { leave, queryFirst, waitFor } from "@odoo/hoot-dom";
import {
    animationFrame,
    disableAnimations,
    enableTransitions,
    runAllTimers,
} from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { TourInteractive } from "@web_tour/js/tour_interactive/tour_interactive";

describe.current.tags("desktop");

class Counter extends Component {
    static props = ["*"];
    static template = xml/*html*/ `
        <div class="counter">
            <div class="interval">
                <input type="number" t-model.number="state.interval" />
            </div>
            <div class="counter">
                <span class="value" t-esc="state.value" />
                <button class="inc" t-on-click="onIncrement">+</button>
            </div>
        </div>
    `;
    setup() {
        this.state = useState({ interval: 1, value: 0 });
    }
    onIncrement() {
        this.state.value += this.state.interval;
    }
}

const tourRegistry = registry.category("web_tour.tours");
const tourConsumed = [];

beforeEach(() => {
    patchWithCleanup(console, {
        error: () => {},
        warn: () => {},
        log: () => {},
        dir: () => {},
    });
    onRpc("web_tour.tour", "consume", ({ args }) => {
        tourConsumed.push(args[0]);
        const nextTour = tourRegistry
            .getEntries()
            .filter(([tourName]) => !tourConsumed.includes(tourName))
            .at(0);
        return (nextTour && { name: nextTour.at(0) }) || false;
    });
    onRpc("res.users", "switch_tour_enabled", () => true);
});

after(() => {
    TourInteractive.observer.disconnect();
});

test("scrolling to next step should update the pointer's height", async (assert) => {
    disableAnimations();

    const content = "Click this pretty button to increment this magnificent counter !";
    registry.category("web_tour.tours").add("tour_de_france", {
        steps: () => [
            {
                trigger: "button.inc",
                content,
                run: "click",
            },
        ],
    });
    enableTransitions();
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                <Counter />
                <div class="bottom-filler" style="height: 300px" />
                <button class="other">Vingegaard</button>
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_de_france", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    const firstOpenRect = queryFirst(".o_tour_pointer_tip").getBoundingClientRect();
    const firstOpenWidth = Math.floor(firstOpenRect.width);
    const firstOpenHeight = Math.floor(firstOpenRect.height);
    expect(firstOpenWidth).toBe(39);
    expect(firstOpenHeight).toBe(44);

    await contains(".o_tour_pointer_tip").hover();
    expect(".o_tour_pointer_content").toHaveCount(1);
    expect(".o_tour_pointer_content span").toHaveText(content);
    await contains(".interval input").click();
    expect(".o_tour_pointer_content").toHaveCount(0);

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await runAllTimers();
    await animationFrame(); // awaits the intersection observer to update after the scroll
    // now the scroller pointer should be shown
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".o_tour_pointer_tip").hover();
    await animationFrame();
    expect(".o_tour_pointer span").toHaveText("Scroll up to reach the next step.");
    await contains(".o_tour_pointer_content").click();

    await runAllTimers();
    // awaits the intersection observer to update after the scroll
    await animationFrame();
    // now the true step pointer should be shown again
    expect(".o_tour_pointer_tip").toHaveCount(1);
    expect(".o_tour_pointer_content").toHaveCount(0);

    await contains(".o_tour_pointer_tip").hover();
    expect(".o_tour_pointer_content").toHaveCount(1);

    expect(".o_tour_pointer span").toHaveText(content);
    await contains(".interval input").click();
    const secondOpenRect = queryFirst(".o_tour_pointer_tip").getBoundingClientRect();
    const secondOpenWidth = Math.floor(secondOpenRect.width);
    const secondOpenHeight = Math.floor(secondOpenRect.height);
    expect(secondOpenHeight).toEqual(firstOpenHeight);
    expect(secondOpenWidth).toEqual(firstOpenWidth);

    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("should show only 1 pointer at a time", async () => {
    registry.category("web_tour.tours").add("milan_sanremo", {
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
            },
        ],
    });
    registry.category("web_tour.tours").add("paris_roubaix", {
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <t>
                <Counter />
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("paris_roubaix", { mode: "manual" });
    await getService("tour_service").startTour("milan_sanremo", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".interval input").edit(5);
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("hovering to the anchor element should show the content and not when content empty", async () => {
    registry.category("web_tour.tours").add("la_vuelta", {
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <t>
                <Counter />
                <button class="other">Pogačar</button>
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("la_vuelta", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    expect(".o_tour_pointer_content").toHaveCount(0);
    await contains(".o_tour_pointer_tip").hover();
    await animationFrame();
    expect(".o_tour_pointer_content").toHaveCount(1);
    expect(".o_tour_pointer_content span").toHaveText("content");
    await contains(".other").click();
    await animationFrame();
    expect(".o_tour_pointer_content").toHaveCount(0);

    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
    expect(".o_tour_pointer_content").toHaveCount(1);
    await contains("button.inc").click();
    await advanceTime(400);
    expect(".o_tour_pointer_content").toHaveCount(0);
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("pointer is added on top of overlay's stack", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: ".modal .a", run: "click" },
            { trigger: ".btn-primary", run: "click" },
        ],
    });
    class DummyDialog extends Component {
        static props = ["*"];
        static components = { Dialog };
        static template = xml`
            <Dialog>
                <button class="a">A</button>
                <button class="b">B</button>
            </Dialog>
        `;
    }
    class Root extends Component {
        static props = ["*"];
        static components = {};
        static template = xml``;
    }

    await mountWithCleanup(Root);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    getService("dialog").add(DummyDialog, {});
    await animationFrame();
    expect(`.o-overlay-item`).toHaveCount(2);
    // the pointer should be after the dialog
    expect(".o-overlay-item:eq(0) .modal").toHaveCount(1);
    await animationFrame();
    expect(".o-overlay-item:eq(1) .o_tour_pointer").toHaveCount(1);

    await contains(".modal .a").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains(".btn-primary").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("next step with new anchor at same position", async () => {
    tourRegistry.add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static template = xml/*html*/ `
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
        `;
    }
    class Root extends Component {
        static props = ["*"];
        static components = { Dummy };
        static template = xml/*html*/ `
            <t>
                <Dummy />
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);

    // check position of the pointer relative to the foo button
    let pointerRect = queryFirst(".o_tour_pointer_tip").getBoundingClientRect();
    let buttonRect = queryFirst("button.foo").getBoundingClientRect();
    const leftValue1 = pointerRect.left - buttonRect.left;
    const bottomValue1 = pointerRect.bottom - buttonRect.bottom;
    expect(leftValue1).not.toBe(0);
    expect(bottomValue1).not.toBe(0);

    await contains("button.foo").click();
    expect(".o_tour_pointer_tip").toHaveCount(0);
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);

    // check position of the pointer relative to the bar button
    pointerRect = queryFirst(".o_tour_pointer_tip").getBoundingClientRect();
    buttonRect = queryFirst("button.bar").getBoundingClientRect();
    const leftValue2 = pointerRect.left - buttonRect.left;
    const bottomValue2 = pointerRect.bottom - buttonRect.bottom;
    expect(Math.round(bottomValue1)).toBe(Math.round(bottomValue2));
    expect(leftValue1).toBe(leftValue2);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("points to next step", async () => {
    tourRegistry.add("tour1", {
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml`
            <t>
                <Counter />
            </t>`;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer_tip").toHaveCount(0);
    expect("span.value").toHaveText("1");
});

test("scroller pointer to reach next step", async () => {
    disableAnimations();

    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [
            { trigger: "button.inc", content: "Click to increment", run: "click" },
            { trigger: "button.test", run: "click" },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                <button class="test">Test me</button>
                <div class="top-filler" style="height: 500px" />
                <Counter />
                <div class="bottom-filler" style="height: 500px" />
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });

    await animationFrame();
    expect(".o_tour_pointer .o_tour_pointer_tip").toHaveCount(1);
    await contains(".o_tour_pointer_tip").hover();
    await contains(".o_tour_pointer_content:contains(Scroll down to reach the next step.)").click();
    await leave();

    await contains(".o_tour_pointer_tip").hover();
    expect(".o_tour_pointer_content span").toHaveText("Click to increment");

    expect(".counter .value").toHaveText("0");

    await contains("button.inc").click();
    await animationFrame();

    expect(".counter .value").toHaveText("1");
    expect(".o_tour_pointer_content").toHaveCount(0);
    expect(".o_tour_pointer_tip").toHaveCount(1);

    await contains(".o_tour_pointer_tip").hover();
    await contains(".o_tour_pointer:contains(Scroll up to reach the next step.)").click();
    await animationFrame();

    await contains("button.test").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scroller pointer to reach next step (X axis)", async () => {
    disableAnimations();
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [
            { trigger: "button.inc", content: "Click to increment", run: "click" },
            { trigger: "button.test", run: "click" },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent d-flex flex-row" style="overflow-x: scroll; width: 300px;">
                <button class="test">Test me</button>
                <div class="left-filler" style="min-width: 500px" />
                <Counter />
                <div class="right-filler" style="min-width: 500px" />
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });
    await animationFrame();

    await contains(".o_tour_pointer_tip").hover();
    await contains(".o_tour_pointer:contains(Scroll right to reach the next step.)").click();
    await leave();
    await animationFrame();

    await contains(".o_tour_pointer_tip").hover();
    expect(".o_tour_pointer_content span").toHaveText(`Click to increment`);

    expect(".counter .value").toHaveText("0");

    await contains("button.inc").click();
    await animationFrame();

    expect(".counter .value").toHaveText("1");
    expect(".o_tour_pointer_tip").toHaveCount(1);

    await contains(".o_tour_pointer_tip").hover();
    await contains(".o_tour_pointer:contains(Scroll left to reach the next step.)").click();
    await animationFrame();

    await contains("button.test").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("check tooltip position", async () => {
    registry.category("web_tour.tours").add("tour_des_tooltip", {
        steps: () => [
            {
                trigger: ".button0",
                tooltipPosition: "right",
                run: "click",
            },
            {
                trigger: ".button1",
                tooltipPosition: "left",
                run: "click",
            },
            {
                trigger: ".button2",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".button3",
                tooltipPosition: "top",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3 d-flex justify-content-center"><button class="button0">Button 0</button></div>
                    <div class="p-3 d-flex justify-content-center"><button class="button1">Button 1</button></div>
                    <div class="p-3 d-flex justify-content-center"><button class="button2">Button 2</button></div>
                    <div class="p-3 d-flex justify-content-center"><button class="button3">Button 3</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    let tooltip, content;
    enableTransitions();
    await getService("tour_service").startTour("tour_des_tooltip", { mode: "manual" });

    await animationFrame();
    tooltip = await waitFor(".o_tour_pointer");
    const button0 = await waitFor(".button0");
    expect(tooltip.getBoundingClientRect().left).toBeGreaterThan(
        button0.getBoundingClientRect().right
    );
    await contains(".o_tour_pointer_tip").hover();
    content = await waitFor(".o_tour_pointer_content");
    expect(content.getBoundingClientRect().left).toBeGreaterThan(
        button0.getBoundingClientRect().right
    );
    await contains(".button0").click();

    await animationFrame();
    tooltip = await waitFor(".o_tour_pointer");
    const button1 = await waitFor(".button1");
    expect(tooltip.getBoundingClientRect().right).toBeLessThan(
        button1.getBoundingClientRect().left
    );
    await contains(".o_tour_pointer_tip").hover();
    content = await waitFor(".o_tour_pointer_content");
    expect(content.getBoundingClientRect().right).toBeLessThan(
        button1.getBoundingClientRect().left
    );
    await contains(".button1").click();

    await animationFrame();
    tooltip = await waitFor(".o_tour_pointer");
    const button2 = await waitFor(".button2");
    expect(tooltip.getBoundingClientRect().top).toBeGreaterThan(
        button2.getBoundingClientRect().bottom
    );
    await contains(".o_tour_pointer_tip").hover();
    content = await waitFor(".o_tour_pointer_content");
    expect(content.getBoundingClientRect().top).toBeGreaterThan(
        button2.getBoundingClientRect().bottom
    );
    await contains(".button2").click();

    await animationFrame();
    tooltip = await waitFor(".o_tour_pointer");
    const button3 = await waitFor(".button3");
    expect(tooltip.getBoundingClientRect().bottom).toBeLessThan(
        button3.getBoundingClientRect().top
    );
    await contains(".o_tour_pointer_tip").hover();
    content = await waitFor(".o_tour_pointer_content");
    expect(content.getBoundingClientRect().bottom).toBeLessThan(
        button3.getBoundingClientRect().top
    );
    await contains(".button3").click();
});

test("check drop zone", async () => {
    registry.category("web_tour.tours").add("tour_des_drag_and_drop", {
        steps: () => [
            {
                trigger: ".hello",
                run: "drag_and_drop .drop_zone",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="hello o-draggable p-3">Drag me please</div>
                    <div class="p-3">Other div</div>
                    <div class="p-3">Other div</div>
                    <div class="p-3">Other div</div>
                    <div class="p-3">Other div</div>
                    <div class="p-3">Other div</div>
                    <div class="p-3">Other div</div>
                    <div class="drop_zone p-3" style="width:145px; height:133px; margin-left:56px; margin-top:78px;">
                        Drop here !
                    </div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_drag_and_drop", { mode: "manual" });
    await animationFrame();
    await contains(".hello").drag();
    expect(".o_tour_dropzone").toHaveCount(1);
    const rect = queryFirst(".drop_zone").getBoundingClientRect();
    expect(".o_tour_dropzone").toHaveRect(rect);
});
