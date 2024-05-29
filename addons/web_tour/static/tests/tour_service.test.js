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
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { queryFirst } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { session } from "@web/session";
import { MacroEngine } from "@web/core/macro";

describe.current.tags("headless");

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

beforeEach(() => {
    patchWithCleanup(MacroEngine.prototype, {
        start() {
            super.start(...arguments);
            macroEngines.push(this);
        },
    });
    macroEngines.forEach((e) => e.stop());
    macroEngines = [];
    onRpc("/web/dataset/call_kw/web_tour.tour/consume", async () => {
        return Promise.resolve(true);
    });
});

afterEach(() => {
    clearRegistry(tourRegistry);
});

test("Tours sequence", async () => {
    tourRegistry
        .add("Tour 1", {
            sequence: 10,
            steps: () => [
                {
                    trigger: ".anchor",
                },
            ],
        })
        .add("Tour 2", {
            steps: () => [
                {
                    trigger: ".anchor",
                },
            ],
        })
        .add("Tour 3", {
            sequence: 5,
            steps: () => [
                {
                    trigger: ".anchor",
                    content: "Oui",
                },
            ],
        });
    await makeMockEnv();
    const sortedTours = getService("tour_service").getSortedTours();
    expect(sortedTours[0].name).toBe("Tour 3");
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
        sequence: 10,
        steps: () => steps,
    });
    await makeMockEnv({});
    const waited_error1 = `Error for step ${JSON.stringify(
        steps[0],
        null,
        4
    )}\nInvalid object: unknown key 'Belgium', unknown key 'wins', unknown key 'EURO2024'`;
    const waited_error2 = `Error for step ${JSON.stringify(
        steps[1],
        null,
        4
    )}\nInvalid object: unknown key 'my_title', unknown key 'doku'`;
    const waited_error3 = `Error for step ${JSON.stringify(
        steps[2],
        null,
        4
    )}\nInvalid object: 'run' is not a string or function`;
    getService("tour_service").startTour("tour1");
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
    const sortedTours = getService("tour_service").getSortedTours();
    expect(sortedTours).toHaveLength(1);
    expect(sortedTours[0].steps).toEqual([{ trigger: "#2" }]);
    expect(sortedTours[0].name).toBe("homepage");
});

test("points to next step", async () => {
    tourRegistry.add("tour1", {
        sequence: 10,
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await makeMockEnv();

    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml`
            <t>
                <Counter />
            </t>`;
    }

    await mountWithCleanup(Root);
    getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect("span.value").toHaveText("1");
});

test("next step with new anchor at same position", async () => {
    tourRegistry.add("tour1", {
        sequence: 10,
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });
    await makeMockEnv();

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
    getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the foo button
    let pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    let buttonRect = queryFirst("button.foo").getBoundingClientRect();
    const leftValue1 = pointerRect.left - buttonRect.left;
    const bottomValue1 = pointerRect.bottom - buttonRect.bottom;
    expect(leftValue1 !== 0).toBe(true);
    expect(bottomValue1 !== 0).toBe(true);

    await contains("button.foo").click();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the bar button
    pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    buttonRect = queryFirst("button.bar").getBoundingClientRect();
    const leftValue2 = pointerRect.left - buttonRect.left;
    const bottomValue2 = pointerRect.bottom - buttonRect.bottom;
    expect(Math.round(bottomValue1)).toBe(Math.round(bottomValue2));
    expect(leftValue1).toBe(leftValue2);
});

test("a failing tour logs the step that failed in run", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    await makeMockEnv();
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
        test: true,
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run() {
                    const el = document.querySelector(".wrong_selector");
                    el.click();
                },
            },
        ],
    });
    getService("tour_service").startTour("tour2", { mode: "auto" });
    await advanceTime(750);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour2 on step: '.button0'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour2 on step: '.button1'"]);
    await advanceTime(750);

    const expectedError = [
        `error: Tour tour2 failed at step .button1. Element has been found. The error seems to be with step.run`,
        "error: Cannot read properties of null (reading 'click')",
        "error: tour not succeeded",
    ];
    expect.verifySteps(expectedError);
});

test("a failing tour with disabled element", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    await makeMockEnv();
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
        test: true,
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
    getService("tour_service").startTour("tour3", { mode: "auto" });
    await advanceTime(750);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour3 on step: '.button0'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour3 on step: '.button1'"]);
    await advanceTime(750);
    await advanceTime(10000);

    const expectedError = [
        `error: Tour tour3 failed at step .button1. Element has been found but is disabled.`,
    ];
    expect.verifySteps(expectedError);
});

test("a failing tour logs the step that failed", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => expect.step(`warn: ${s.replace(/[ \n\-/\r\t]/gi, "")}`),
        error: (s) => expect.step(`error: ${s}`),
    });
    await makeMockEnv();

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
        test: true,
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
    getService("tour_service").startTour("tour1", { mode: "auto" });
    await advanceTime(750);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour1 on step: 'content (trigger: .button0)'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour1 on step: 'content (trigger: .button1)'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour1 on step: 'content (trigger: .button2)'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour1 on step: 'content (trigger: .button3)'"]);
    await advanceTime(750);
    expect.verifySteps(["log: Tour tour1 on step: 'content (trigger: .wrong_selector)'"]);
    await advanceTime(10000);
    const expectedWarning = `warn: Tourtour1failedatstepcontent(trigger:.wrong_selector){"content":"content","trigger":".button1","run":"click"},{"content":"content","trigger":".button2","run":"click"},{"content":"content","trigger":".button3","run":"click"},FAILINGSTEP(59){"content":"content","trigger":".wrong_selector","run":"click"},{"content":"content","trigger":".button4","run":"click"},{"content":"content","trigger":".button5","run":"click"},{"content":"content","trigger":".button6","run":"click"},`;
    const expectedError = `error: Tour tour1 failed at step content (trigger: .wrong_selector). The cause is that trigger (.wrong_selector) element cannot be found in DOM.`;
    expect.verifySteps([expectedWarning, expectedError]);
});

test("check tour with inactive steps", async () => {
    await makeMockEnv();

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
        test: true,
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
    getService("tour_service").startTour("pipu_tour", { mode: "auto" });
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
        sequence: 10,
        steps: () => [
            { trigger: ".modal .a", run: "click" },
            { trigger: ".open", run: "click" },
        ],
    });
    await makeMockEnv({});
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

    getService("tour_service").startTour("tour1", { mode: "manual" });
    getService("dialog").add(DummyDialog, {});
    await advanceTime(100);
    expect(`.o-overlay-item`).toHaveCount(2);
    // the pointer should be after the dialog
    expect(".o-overlay-item:eq(0) .modal").toHaveCount(1);
    await advanceTime(100);
    expect(".o-overlay-item:eq(1) .o_tour_pointer").toHaveCount(1);
});

test("registering test tour after service is started doesn't auto-start the tour", async () => {
    patchWithCleanup(session, { tour_disable: false });
    await makeMockEnv();

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
        test: true,
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(0);
});

test("registering non-test tour after service is started auto-starts the tour", async () => {
    patchWithCleanup(session, { tour_disable: false });
    await makeMockEnv();

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
    registry.category("web_tour.tours").add("liege_bastogne_liege", {
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);
});

test("hovering to the anchor element should show the content", async () => {
    registry.category("web_tour.tours").add("la_vuelta", {
        sequence: 10,
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await makeMockEnv();
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
    getService("tour_service").startTour("la_vuelta", { mode: "manual" });
    await animationFrame();
    await advanceTime(750);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer_content:not(.invisible)").toHaveCount(1);
    expect(".o_tour_pointer_content:not(.invisible)").toHaveText("content");
    await contains(".other").hover();
    await animationFrame();
    expect(".o_tour_pointer_content.invisible").toHaveCount(1);
});

test("should show only 1 pointer at a time", async () => {
    registry.category("web_tour.tours").add("milan_sanremo", {
        sequence: 10,
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
            },
        ],
    });
    registry.category("web_tour.tours").add("paris_roubaix", {
        sequence: 10,
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await makeMockEnv();
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
    getService("tour_service").startTour("paris_roubaix", { mode: "manual" });
    getService("tour_service").startTour("milan_sanremo", { mode: "manual" });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(0);
    await advanceTime(750);
    expect(".o_tour_pointer").toHaveCount(1);
});

test("perform edit on next step", async () => {
    registry.category("web_tour.tours").add("giro_d_italia", {
        sequence: 10,
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
    await makeMockEnv();
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
    getService("tour_service").startTour("giro_d_italia", { mode: "manual" });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(0);
    await advanceTime(750);
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    await expect(".counter .value").toHaveText("5");
});

test("scrolling to next step should update the pointer's height", async (assert) => {
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

    const stepContent = "Click this pretty button to increment this magnificent counter !";
    registry.category("web_tour.tours").add("tour_de_france", {
        sequence: 10,
        steps: () => [
            {
                trigger: "button.inc",
                content: stepContent,
                run: "click",
            },
        ],
    });
    await makeMockEnv();

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
    getService("tour_service").startTour("tour_de_france", { mode: "manual" });
    await animationFrame();
    await advanceTime(100); // awaits the macro engine
    const pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe(stepContent);
    expect(pointer).not.toHaveClass("o_open");
    expect(pointer.style.height).toBe("28px");
    expect(pointer.style.width).toBe("28px");

    await contains(pointer).hover();
    const firstOpenHeight = pointer.style.height;
    const firstOpenWidth = pointer.style.width;

    await advanceTime(100); // awaits for the macro engine next check cycle
    expect(pointer).toHaveClass("o_open");
    await contains(".other").hover();

    await advanceTime(100); // awaits for the macro engine next check cycle
    expect(".o_tour_pointer").not.toHaveClass("o_open");

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await animationFrame(); // awaits the intersection observer to update after the scroll
    await advanceTime(100); // awaits for the macro engine next check cycle
    // now the scroller pointer should be shown
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Scroll up to reach the next step.");

    await contains(".scrollable-parent").scroll({ top: 0 });
    await animationFrame(); // awaits the intersection observer to update after the scroll
    await advanceTime(100); // awaits for the macro engine next check cycle
    // now the true step pointer should be shown again
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe(stepContent);

    await contains(".o_tour_pointer").hover();
    await animationFrame(); // awaits the intersection observer to update after the scroll
    await advanceTime(100); // awaits for the macro engine next check cycle
    expect(pointer).toHaveClass("o_open");
    const secondOpenHeight = pointer.style.height;
    const secondOpenWidth = pointer.style.width;
    expect(secondOpenHeight).toEqual(firstOpenHeight);
    expect(secondOpenWidth).toEqual(firstOpenWidth);
});

test("scroller pointer to reach next step", async () => {
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

    registry.category("web_tour.tours").add("tour_des_flandres", {
        sequence: 10,
        steps: () => [{ trigger: "button.inc", content: "Click to increment", run: "click" }],
    });
    await makeMockEnv();
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
    getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });
    await animationFrame();
    await advanceTime(100); // awaits the macro engine

    // Even if this seems weird, it should show the initial pointer.
    // This is due to the fact the intersection observer has just been started and
    // the pointer did not have the observations yet when the pointTo method was called.
    // This is a bit tricky to change for now because the synchronism of the pointTo method
    // is what permits to avoid multiple pointer to be shown at the same time
    let pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");

    await animationFrame();
    await advanceTime(100); // awaits for the macro engine next check cycle
    // now the scroller pointer should be shown
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Scroll down to reach the next step.");

    // awaiting the click here permits to the intersection observer to update
    await contains(".o_tour_pointer").click();
    expect(".o_tour_pointer").toHaveCount(0);

    await animationFrame();
    await advanceTime(700); // awaits for the macro engine next check cycle
    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await animationFrame();
    await advanceTime(100); // awaits for the macro engine next check cycle
    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Scroll up to reach the next step.");

    // awaiting the click here permits to the intersection observer to update
    await contains(".o_tour_pointer").click();
    expect(".o_tour_pointer").toHaveCount(0);

    await animationFrame();
    await advanceTime(100); // awaits for the macro engine next check cycle
    pointer = queryFirst(".o_tour_pointer");
    expect(pointer).toHaveCount(1);
    expect(pointer.textContent).toBe("Click to increment");
});

test("manual tour with inactive steps", async () => {
    registry.category("web_tour.tours").add("tour_de_wallonie", {
        rainbowMessage: "bravo",
        sequence: 10,
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
    getService("tour_service").startTour("tour_de_wallonie", { mode: "manual" });
    await animationFrame();
    await advanceTime(100);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(0);
    await advanceTime(750);
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect(".counter .value").toHaveText("5");
    await advanceTime(10000);
});
