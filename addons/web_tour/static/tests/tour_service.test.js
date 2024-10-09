/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    clearRegistry,
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { Component, useState, xml } from "@odoo/owl";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { click, queryFirst, waitFor } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { session } from "@web/session";
import { MacroEngine } from "@web/core/macro";
import { tourState } from "@web_tour/tour_service/tour_state";

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
let macroEngines = [];
const tourConsumed = [];

beforeEach(() => {
    patchWithCleanup(MacroEngine.prototype, {
        start() {
            super.start(...arguments);
            macroEngines.push(this);
        },
    });
    patchWithCleanup(console, {
        error: () => {},
        warn: () => {},
        log: () => {},
        dir: () => {},
    });
    macroEngines.forEach((e) => e.stop());
    macroEngines = [];
    onRpc("/web/dataset/call_kw/web_tour.tour/consume", async (request) => {
        const { params } = await request.json();
        tourConsumed.push(params.args[0]);
        const nextTour = tourRegistry
            .getEntries()
            .filter(([tourName]) => !tourConsumed.includes(tourName))
            .at(0);
        return (nextTour && { name: nextTour.at(0) }) || false;
    });
    onRpc("/web/dataset/call_kw/res.users/switch_tour_enabled", async () => {
        return true;
    });
    onRpc("/web/dataset/call_kw/web_tour.tour/get_tour_json_by_name", async () => {
        return {
            name: "tour1",
            steps: [
                { trigger: "button.foo", run: "click" },
                { trigger: "button.bar", run: "click" },
            ],
        };
    });
});

afterEach(() => {
    clearRegistry(tourRegistry);
});

test("Step Tour validity", async () => {
    patchWithCleanup(console, {
        error: (msg) => expect.step(msg),
    });
    const steps = [
        {
            Belgium: true,
            wins: "of course",
            EURO2024: true,
            trigger: "button.foo",
        },
        {
            my_title: "EURO2024",
            trigger: "button.bar",
            doku: "Lukaku 10",
        },
        {
            trigger: "button.bar",
            run: ["Enjoy euro 2024"],
        },
        {
            trigger: "button.bar",
            run() {},
        },
    ];
    tourRegistry.add("tour1", {
        steps: () => steps,
    });
    await makeMockEnv({});
    const waited_error1 = `Error in schema for TourStep ${JSON.stringify(
        steps[0],
        null,
        4
    )}\nInvalid object: unknown key 'Belgium', unknown key 'wins', unknown key 'EURO2024'`;
    const waited_error2 = `Error in schema for TourStep ${JSON.stringify(
        steps[1],
        null,
        4
    )}\nInvalid object: unknown key 'my_title', unknown key 'doku'`;
    const waited_error3 = `Error in schema for TourStep ${JSON.stringify(
        steps[2],
        null,
        4
    )}\nInvalid object: 'run' is not a string or function or boolean`;
    await getService("tour_service").startTour("tour1");
    await animationFrame();
    expect.verifySteps([waited_error1, waited_error2, waited_error3]);
});

test("override existing tour by using saveAs", async () => {
    tourRegistry
        .add("Tour 1", {
            steps: () => [{ trigger: "#1" }],
            saveAs: "homepage",
        })
        .add("Tour 2", {
            steps: () => [{ trigger: "#2" }],
            saveAs: "homepage",
        });
    await makeMockEnv({});
    await getService("tour_service").startTour("homepage");
    await animationFrame();
    expect(tourState.getCurrentTour()).toBe("Tour 2");
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect("span.value").toHaveText("1");
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
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the foo button
    let pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    let buttonRect = queryFirst("button.foo").getBoundingClientRect();
    const leftValue1 = pointerRect.left - buttonRect.left;
    const bottomValue1 = pointerRect.bottom - buttonRect.bottom;
    expect(leftValue1 !== 0).toBe(true);
    expect(bottomValue1 !== 0).toBe(true);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the bar button
    pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    buttonRect = queryFirst("button.bar").getBoundingClientRect();
    const leftValue2 = pointerRect.left - buttonRect.left;
    const bottomValue2 = pointerRect.bottom - buttonRect.bottom;
    expect(Math.round(bottomValue1)).toBe(Math.round(bottomValue2));
    expect(leftValue1).toBe(leftValue2);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("a failing tour logs the step that failed in run", async () => {
    patchWithCleanup(browser.console, {
        groupCollapsed: (s) => expect.step(`log: ${s}`),
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
                <button class="button2">Button 2</button>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    tourRegistry.add("tour2", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run() {
                    const el = queryFirst(".wrong_selector");
                    el.click();
                },
            },
        ],
    });
    await odoo.startTour("tour2", { mode: "auto" }); // Use odoo to run tour from registry because this is a test tour
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);

    const expectedError = [
        "log: [1/2] Tour tour2 → Step .button0",
        `log: [2/2] Tour tour2 → Step .button1`,
        [
            "error: FAILED: [2/2] Tour tour2 → Step .button1.",
            "Element has been found. The error seems to be with step.run.",
            "Cannot read properties of null (reading 'click')",
        ].join("\n"),
        "error: tour not succeeded",
    ];
    expect.verifySteps(expectedError);
});

test("a failing tour with disabled element", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => {},
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <button class="button0">Button 0</button>
                <button class="button1" disabled="">Button 1</button>
                <button class="button2">Button 2</button>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    tourRegistry.add("tour3", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run: "click",
            },
            {
                trigger: ".button2",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour3", { mode: "auto" });
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    const expectedError = [
        [
            `error: FAILED: [2/3] Tour tour3 → Step .button1.`,
            `Element has been found. The error seems to be with step.run.`,
            `Element can't be disabled when you want to click on it.`,
            `Tip: You can add the ":enabled" pseudo selector to your selector to wait for the element is enabled.`,
        ].join("\n"),
        `error: tour not succeeded`,
    ];
    await advanceTime(10000);
    expect.verifySteps(expectedError);
});

test("a failing tour logs the step that failed", async () => {
    patchWithCleanup(browser.console, {
        dir: (s) => expect.step(`runbot: ${s.replace(/[\s-]*/g, "")}`),
        groupCollapsed: (s) => expect.step(`log: ${s}`),
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => expect.step(`warn: ${s.replace(/[\s-]*/gi, "")}`),
        error: (s) => expect.step(`error: ${s}`),
    });

    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
                <button class="button2">Button 2</button>
                <button class="button3">Button 3</button>
                <button class="button4">Button 4</button>
                <button class="button5">Button 5</button>
                <button class="button6">Button 6</button>
                <button class="button7">Button 7</button>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    tourRegistry.add("tour1", {
        steps: () => [
            {
                content: "content",
                trigger: ".button0",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button1",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button2",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button3",
                run: "click",
            },
            {
                content: "content",
                trigger: ".wrong_selector",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button4",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button5",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button6",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button7",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour1", { mode: "auto" });
    await advanceTime(750);
    expect.verifySteps(["log: [1/9] Tour tour1 → Step content (trigger: .button0)"]);
    await advanceTime(750);
    expect.verifySteps(["log: [2/9] Tour tour1 → Step content (trigger: .button1)"]);
    await advanceTime(750);
    expect.verifySteps(["log: [3/9] Tour tour1 → Step content (trigger: .button2)"]);
    await advanceTime(750);
    expect.verifySteps(["log: [4/9] Tour tour1 → Step content (trigger: .button3)"]);
    await advanceTime(750);
    expect.verifySteps(["log: [5/9] Tour tour1 → Step content (trigger: .wrong_selector)"]);
    await advanceTime(10000);
    expect.verifySteps([
        "error: FAILED: [5/9] Tour tour1 → Step content (trigger: .wrong_selector).\nThe cause is that trigger (.wrong_selector) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.",
        `runbot: {"content":"content","trigger":".button1","run":"click"},{"content":"content","trigger":".button2","run":"click"},{"content":"content","trigger":".button3","run":"click"},FAILED:[5/9]Tourtour1→Stepcontent(trigger:.wrong_selector){"content":"content","trigger":".wrong_selector","run":"click"},{"content":"content","trigger":".button4","run":"click"},{"content":"content","trigger":".button5","run":"click"},{"content":"content","trigger":".button6","run":"click"},`,
    ]);
});

test("check tour with inactive steps", async () => {
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">Button 0</button>
                    <button class="button1">Button 1</button>
                    <button class="button2">Button 2</button>
                </div>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    registry.category("web_tour.tours").add("pipu_tour", {
        steps: () => [
            {
                isActive: [".container:not(:has(.this_selector_is_not_here))"],
                trigger: ".button0",
                run() {
                    expect.step("this action 1 has not been skipped");
                },
            },
            {
                isActive: [".container:not(:has(.button0))"],
                trigger: ".button1",
                run() {
                    expect.step("this action 2 has been skipped");
                },
            },
            {
                isActive: [".container:not(:has(.this_selector_is_not_here))"],
                trigger: ".button2",
                run() {
                    expect.step("this action 3 has not been skipped");
                },
            },
        ],
    });
    await odoo.startTour("pipu_tour", { mode: "auto" });
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    expect.verifySteps(["this action 1 has not been skipped"]);
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    expect.verifySteps(["this action 3 has not been skipped"]);
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
    await advanceTime(100);
    expect(`.o-overlay-item`).toHaveCount(2);
    // the pointer should be after the dialog
    expect(".o-overlay-item:eq(0) .modal").toHaveCount(1);
    await advanceTime(100);
    expect(".o-overlay-item:eq(1) .o_tour_pointer").toHaveCount(1);

    await click(".modal .a");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await click(".btn-primary");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("registering test tour after service is started doesn't auto-start the tour", async () => {
    patchWithCleanup(session, { tour_enabled: true });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
                <t>
                    <Counter />
                </t>
            `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    expect(".o_tour_pointer").toHaveCount(0);
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer_content:not(.invisible)").toHaveCount(1);
    expect(".o_tour_pointer_content:not(.invisible)").toHaveText("content");
    await contains(".other").hover();
    await animationFrame();
    expect(".o_tour_pointer_content.invisible").toHaveCount(1);

    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer_content.invisible").toHaveCount(1);

    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("should show only 1 pointer at a time", async () => {
    patchWithCleanup(browser.console, {
        error: (s) => {},
    });
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(1);
    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("perform edit on next step", async () => {
    registry.category("web_tour.tours").add("giro_d_italia", {
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
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
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("giro_d_italia", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".counter .value").toHaveText("5");
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scrolling to next step should update the pointer's height", async (assert) => {
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

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
    expect(".o_tour_pointer").not.toHaveClass("o_open");
    const firstOpenHeight = queryFirst(".o_tour_pointer").style.height;
    const firstOpenWidth = queryFirst(".o_tour_pointer").style.width;
    expect(firstOpenHeight).toBe("28px");
    expect(firstOpenWidth).toBe("28px");

    await contains("button.inc").hover();
    expect(".o_tour_pointer").toHaveText(content);
    expect(".o_tour_pointer").toHaveClass("o_open");
    await contains(".interval input").hover();
    expect(".o_tour_pointer").not.toHaveClass("o_open");

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await runAllTimers();
    await animationFrame(); // awaits the intersection observer to update after the scroll
    // now the scroller pointer should be shown
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_tour_pointer").hover();
    await animationFrame();
    expect(".o_tour_pointer").toHaveText("Scroll up to reach the next step.");
    await contains(".o_tour_pointer").click();

    await runAllTimers();
    // awaits the intersection observer to update after the scroll
    await animationFrame();
    // now the true step pointer should be shown again
    expect(".o_tour_pointer").toHaveCount(1);
    expect(".o_tour_pointer").not.toHaveClass("o_open");

    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer").toHaveClass("o_open");
    expect(".o_tour_pointer").toHaveText(content);
    await contains(".interval input").hover();
    const secondOpenHeight = queryFirst(".o_tour_pointer").style.height;
    const secondOpenWidth = queryFirst(".o_tour_pointer").style.width;
    expect(secondOpenHeight).toEqual(firstOpenHeight);
    expect(secondOpenWidth).toEqual(firstOpenWidth);

    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scroller pointer to reach next step", async () => {
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [{ trigger: "button.inc", content: "Click to increment", run: "click" }],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                <div class="top-filler" style="height: 500px" />
                <Counter />
                <div class="bottom-filler" style="height: 500px" />
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });
    await animationFrame();

    // Even if this seems weird, it should show the initial pointer.
    // This is due to the fact the intersection observer has just been started and
    // the pointer did not have the observations yet when the pointTo method was called.
    // This is a bit tricky to change for now because the synchronism of the pointTo method
    // is what permits to avoid multiple pointer to be shown at the same time
    let pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");

    await animationFrame();
    // now the scroller pointer should be shown
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Scroll down to reach the next step.");

    // awaiting the click here permits to the intersection observer to update
    await contains(".o_tour_pointer").click();
    await advanceTime(1000);
    await animationFrame();

    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await advanceTime(1000);
    await animationFrame();

    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Scroll up to reach the next step.");

    // awaiting the click here permits to the intersection observer to update
    await contains(".o_tour_pointer").click();
    await advanceTime(1000);
    await animationFrame();

    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");

    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("automatic tour with invisible element", async () => {
    patchWithCleanup(browser.console, {
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    await makeMockEnv();

    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">Button 0</button>
                    <button class="button1" style="display:none;">Button 1</button>
                    <button class="button2">Button 2</button>
                </div>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    registry.category("web_tour.tours").add("tour_de_wallonie", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run: "click",
            },
            {
                trigger: ".button2",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour_de_wallonie", { mode: "auto" });
    await animationFrame();
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(750);
    await advanceTime(10000);
    expect.verifySteps([
        "error: FAILED: [2/3] Tour tour_de_wallonie → Step .button1.\nThe cause is that trigger (.button1) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.",
    ]);
});

test("automatic tour with invisible element but use :not(:visible))", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => {
            s.includes("tour succeeded") ? expect.step(`succeeded`) : false;
        },
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    await makeMockEnv();

    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">Button 0</button>
                    <button class="button1" style="display:none;">Button 1</button>
                    <button class="button2">Button 2</button>
                </div>
            </t>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    registry.category("web_tour.tours").add("tour_de_wallonie", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1:not(:visible)",
                run: "click",
            },
            {
                trigger: ".button2",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour_de_wallonie", { mode: "auto" });
    await animationFrame();
    await advanceTime(750);
    await animationFrame();
    await advanceTime(750);
    await animationFrame();
    await advanceTime(750);
    expect.verifySteps(["succeeded"]);
});

test("manual tour with inactive steps", async () => {
    registry.category("web_tour.tours").add("tour_de_wallonie", {
        steps: () => [
            {
                isActive: ["auto"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["auto"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["manual"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["auto"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["manual"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["auto"],
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
    await getService("tour_service").startTour("tour_de_wallonie", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect(".counter .value").toHaveText("5");
    await advanceTime(10000);
});

test("automatic tour with alternative trigger", async () => {
    let suppressLog = false;
    patchWithCleanup(browser.console, {
        groupCollapsed: (s) => {
            expect.step("on step");
            suppressLog = true;
        },
        groupEnd: () => {
            suppressLog = false;
        },
        log: (s) => {
            if (suppressLog) {
                return;
            }
            if (s.toLowerCase().includes("tour tour_des_flandres succeeded")) {
                expect.step("succeeded");
            } else if (s !== "tour succeeded") {
                expect.step("on step");
            }
        },
    });
    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [
            {
                trigger: ".interval, .button1",
            },
            {
                trigger: ".interval, .button3",
            },
            {
                trigger: ".interval1, .interval2, .button4",
            },
            {
                trigger: ".button5",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">Button 0</button>
                    <button class="button1">Button 1</button>
                    <button class="button2">Button 2</button>
                    <button class="button3">Button 3</button>
                    <button class="button4">Button 4</button>
                    <button class="button5">Button 5</button>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    await odoo.startTour("tour_des_flandres", { mode: "auto" });
    for (let i = 0; i <= 5; i++) {
        await advanceTime(750);
    }
    await advanceTime(10000);
    expect.verifySteps(["on step", "on step", "on step", "on step", "succeeded"]);
});

test("manual tour with alternative trigger", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => {
            !s.includes("═") ? expect.step(s) : "";
        },
    });
    registry.category("web_tour.tours").add("tour_des_flandres_2", {
        steps: () => [
            {
                trigger: ".button1, .button2",
                run: "click",
            },
            {
                trigger: "body:not(:visible), .button4, .button3",
                run: "click",
            },
            {
                trigger: ".interval1, .interval2, .button5",
                run: "click",
            },
            {
                trigger: "button:contains(0, hello):enabled, button:contains(2, youpi)",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">0, hello</button>
                    <button class="button1">Button 1</button>
                    <button class="button2">2, youpi</button>
                    <button class="button3">Button 3</button>
                    <button class="button4">Button 4</button>
                    <button class="button5">Button 5</button>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres_2", { mode: "manual" });
    await contains(".button2").click();
    await contains(".button3").click();
    await contains(".button5").click();
    await contains(".button2").click();
    expect.verifySteps(["click", "click", "click", "click", "tour succeeded"]);
});

test("Tour backward when the pointed element disappear", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="fool w-100" t-on-click="() => { state.bool = true; }">You fool</button>
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.fool").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Tour backward when the pointed element disappear and ignore warn step", async () => {
    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });

    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="fool" t-on-click="() => { state.bool = true; }">You fool</button>
            <button class="foo" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar" t-if="!state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.fool").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
    expect.verifySteps(["Step 'button.bar' ignored.", "Step 'button.bar' ignored."]);
});

test("Tour started by the URL", async () => {
    browser.location.href = `${browser.location.origin}?tour=tour1`;

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Log a warning if step ignored", async () => {
    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });

    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);

    expect.verifySteps(["Step 'button.bar' ignored."]);
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
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3"><button class="button1">Button 1</button></div>
                    <div class="p-3"><button class="button2">Button 2</button></div>
                    <div class="p-3"><button class="button3">Button 3</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    let tooltip;
    await getService("tour_service").startTour("tour_des_tooltip", { mode: "manual" });

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button0 = await waitFor(".button0");
    expect(tooltip.getBoundingClientRect().left).toBeGreaterThan(
        button0.getBoundingClientRect().right
    );
    await contains(".button0").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button1 = await waitFor(".button1");
    expect(tooltip.getBoundingClientRect().right).toBeLessThan(
        button1.getBoundingClientRect().left
    );
    await contains(".button1").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button2 = await waitFor(".button2");
    expect(tooltip.getBoundingClientRect().top).toBeGreaterThan(
        button2.getBoundingClientRect().bottom
    );
    await contains(".button2").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button3 = await waitFor(".button3");
    expect(tooltip.getBoundingClientRect().bottom).toBeLessThan(
        button3.getBoundingClientRect().top
    );
    await contains(".button3").click();
});

test("check rainbowManMessage", async () => {
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run: "click",
            },
            {
                trigger: ".button2",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3"><button class="button1">Button 1</button></div>
                    <div class="p-3"><button class="button2">Button 2</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("rainbow_tour", {
        mode: "manual",
        rainbowManMessage: "Congratulations !",
    });
    await contains(".button0").click();
    await contains(".button1").click();
    await contains(".button2").click();
    const rainbowMan = await waitFor(".o_reward_rainbow_man");
    expect(rainbowMan.getBoundingClientRect().width).toBe(400);
    expect(rainbowMan.getBoundingClientRect().height).toBe(400);
    expect(".o_reward_msg_content").toHaveText("Congratulations !");
});

test("check alternative trigger that appear after the initial trigger", async () => {
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".button0, .button1",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3 add_button"></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    const otherButton = document.createElement("button");
    otherButton.classList.add("button1");
    queryFirst(".add_button").appendChild(otherButton);
    await contains(".button1").click();
    expect(".o_tour_pointer").toHaveCount(0);
});
