/** @odoo-module **/

import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { Macro } from "@web/core/macro";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

describe.current.tags("desktop");

const tourRegistry = registry.category("web_tour.tours");
let macro;
async function waitForMacro() {
    for (let i = 0; i < 50; i++) {
        await animationFrame();
        await advanceTime(265);
        if (macro.isComplete) {
            return;
        }
    }
    if (!macro.isComplete) {
        throw new Error(`Macro is not complete`);
    }
}

beforeEach(() => {
    patchWithCleanup(Macro.prototype, {
        start() {
            super.start(...arguments);
            macro = this;
        },
    });
    patchWithCleanup(console, {
        error: () => {},
        warn: () => {},
        log: () => {},
        dir: () => {},
    });
});

afterEach(() => {
    macro.stop();
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

test("a tour with invalid step trigger", async () => {
    patchWithCleanup(browser.console, {
        groupCollapsed: (s) => expect.step(`log: ${s}`),
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => {},
        error: (s) => expect.step(`error: ${s}`),
    });
    tourRegistry.add("tour_invalid_trigger", {
        steps: () => [
            {
                trigger: ".button0:contins(brol)",
                run: "click",
            },
            {
                trigger: ".button1:has(machin)",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour_invalid_trigger", { mode: "auto" }); // Use odoo to run tour from registry because this is a test tour
    await waitForMacro();
    const expectedSteps = [
        "log: [1/2] Tour tour_invalid_trigger → Step .button0:contins(brol)",
        `error: FAILED: [1/2] Tour tour_invalid_trigger → Step .button0:contins(brol).
ERROR during find trigger:
Failed to execute 'querySelectorAll' on 'Element': '.button0:contins(brol)' is not a valid selector.`,
    ];
    expect.verifySteps(expectedSteps);
});

test("a failing tour logs the step that failed in run", async () => {
    patchWithCleanup(browser.console, {
        groupCollapsed: (s) => expect.step(`log: ${s}`),
        log: (s) => expect.step(`log: ${s}`),
        warn: (s) => {},
        error: (s) => {
            s = s.replace(/\n +at.*/g, ""); // strip stack trace
            expect.step(`error: ${s}`);
        },
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
    await waitForMacro();
    const expectedError = [
        "log: [1/2] Tour tour2 → Step .button0",
        `log: [2/2] Tour tour2 → Step .button1`,
        [
            "error: FAILED: [2/2] Tour tour2 → Step .button1.",
            `TypeError: Cannot read properties of null (reading 'click')`,
        ].join("\n"),
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
        timeout: 500,
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
    await waitForMacro();
    const expectedError = [
        `error: FAILED: [2/3] Tour tour3 → Step .button1.
Element has been found.
BUT: Element is not enabled. TIP: You can use :enable to wait the element is enabled before doing action on it.
TIMEOUT step failed to complete within 500 ms.`,
    ];
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
                timeout: 111,
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
    await waitForMacro();
    expect.verifySteps([
        "log: [1/9] Tour tour1 → Step content (trigger: .button0)",
        "log: [2/9] Tour tour1 → Step content (trigger: .button1)",
        "log: [3/9] Tour tour1 → Step content (trigger: .button2)",
        "log: [4/9] Tour tour1 → Step content (trigger: .button3)",
        "log: [5/9] Tour tour1 → Step content (trigger: .wrong_selector)",
        `error: FAILED: [5/9] Tour tour1 → Step content (trigger: .wrong_selector).
Element (.wrong_selector) has not been found.
TIMEOUT step failed to complete within 111 ms.`,
        `runbot: {"content":"content","trigger":".button1","run":"click"},{"content":"content","trigger":".button2","run":"click"},{"content":"content","trigger":".button3","run":"click"},FAILED:[5/9]Tourtour1→Stepcontent(trigger:.wrong_selector){"content":"content","trigger":".wrong_selector","run":"click","timeout":111},{"content":"content","trigger":".button4","run":"click"},{"content":"content","trigger":".button5","run":"click"},{"content":"content","trigger":".button6","run":"click"},`,
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
    await waitForMacro();
    expect.verifySteps([
        "this action 1 has not been skipped",
        "this action 3 has not been skipped",
    ]);
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
        timeout: 777,
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
    await waitForMacro();
    expect.verifySteps([
        `error: FAILED: [2/3] Tour tour_de_wallonie → Step .button1.
Element has been found.
BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.
TIMEOUT step failed to complete within 777 ms.`,
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
    await waitForMacro();
    expect.verifySteps(["succeeded"]);
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
    await waitForMacro();
    expect.verifySteps(["on step", "on step", "on step", "on step", "succeeded"]);
});

test("check not possible to click below modal", async () => {
    patchWithCleanup(console, {
        warn: () => {},
        error: (s) => expect.step(`error: ${s}`),
        log: (s) => expect.step(`log: ${s}`),
        dir: () => {},
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
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0" t-on-click="openDialog">Button 0</button></div>
                    <div class="p-3"><button class="button1">Button 1</button></div>
                    <div class="p-3"><button class="button2">Button 2</button></div>
                    <div class="p-3"><button class="button3">Button 3</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
        setup() {
            this.dialogService = useService("dialog");
        }
        openDialog() {
            this.dialogService.add(DummyDialog);
        }
    }
    await mountWithCleanup(Root);

    registry.category("web_tour.tours").add("tour_check_modal", {
        timeout: 888,
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour_check_modal", { mode: "auto" });
    await waitForMacro();
    expect.verifySteps([
        "log: [1/2] Tour tour_check_modal → Step .button0",
        "log: [2/2] Tour tour_check_modal → Step .button1",
        `error: FAILED: [2/2] Tour tour_check_modal → Step .button1.
Element has been found.
BUT: It is not allowed to do action on an element that's below a modal.
TIMEOUT step failed to complete within 888 ms.`,
    ]);
});

test("a tour where hoot trigger failed", async () => {
    patchWithCleanup(browser.console, {
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
    tourRegistry.add("tour_hoot_failed", {
        steps: () => [
            {
                content: "content",
                trigger: ".button0",
                run: "click",
            },
            {
                content: "content",
                trigger: ".button1:brol(:machin)",
                run: "click",
            },
        ],
    });
    await odoo.startTour("tour_hoot_failed", { mode: "auto" });
    await waitForMacro();
    expect.verifySteps([
        `error: FAILED: [2/2] Tour tour_hoot_failed → Step content (trigger: .button1:brol(:machin)).
ERROR during find trigger:
Failed to execute 'querySelectorAll' on 'Element': '.button1:brol(:machin)' is not a valid selector.`,
    ]);
});
