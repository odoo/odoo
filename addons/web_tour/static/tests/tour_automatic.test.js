/** @odoo-module native */

import { after, afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import {
    clearRegistry,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { RpcEvent } from "@web/core/events";
import { rpcBus } from "@web/core/network";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Macro } from "@web/core/utils/macro";
import { Dialog } from "@web/ui/dialog";
import { TourAutomatic } from "@web_tour/js/tour_automatic/tour_automatic";
import { tourState } from "@web_tour/js/tour_state";

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
    clearRegistry(tourRegistry);
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
        4,
    )}\nInvalid object: unknown key 'Belgium', unknown key 'wins', unknown key 'EURO2024'`;
    const waited_error2 = `Error in schema for TourStep ${JSON.stringify(
        steps[1],
        null,
        4,
    )}\nInvalid object: unknown key 'my_title', unknown key 'doku'`;
    const waited_error3 = `Error in schema for TourStep ${JSON.stringify(
        steps[2],
        null,
        4,
    )}\nInvalid object: 'run' is not a string or function or boolean`;
    await getService("tour_service").startTour("tour1");
    await animationFrame();
    expect.verifySteps([waited_error1, waited_error2, waited_error3]);
});

test("a step waits for an RPC the previous step left in flight", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);

    const pending = { data: { id: 777 }, url: "/web/dataset/call_kw/x/web_save" };
    tourRegistry.add("tour_settle", {
        steps: () => [
            {
                trigger: ".button0",
                run() {
                    rpcBus.trigger(RpcEvent.REQUEST, pending);
                },
            },
            {
                trigger: ".button1",
                run() {
                    expect.step("second step acted");
                },
            },
        ],
    });

    await odoo.startTour("tour_settle", { mode: "auto" });
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect.verifySteps([]);

    rpcBus.trigger(RpcEvent.RESPONSE, pending);
    await waitForMacro();
    expect.verifySteps(["second step acted"]);
});

test("a step that only observes is neither delayed by in-flight requests nor by a blocked UI", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
            <t>
                <div class="o_blockUI"/>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);

    const pending = { data: { id: 779 }, url: "/website/theme_customize_data" };
    rpcBus.trigger(RpcEvent.REQUEST, pending);
    tourRegistry.add("tour_observe_while_busy", {
        steps: () => [
            {
                trigger: ".button0",
            },
            {
                trigger: ".button1",
                run() {
                    expect.step("action step acted");
                },
            },
        ],
    });

    await odoo.startTour("tour_observe_while_busy", { mode: "auto" });
    await animationFrame();
    await animationFrame();
    expect(tourState.getCurrentIndex()).toBe(1);
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect.verifySteps([]);

    rpcBus.trigger(RpcEvent.RESPONSE, pending);
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect.verifySteps([]);

    queryFirst(".o_blockUI").remove();
    await waitForMacro();
    expect.verifySteps(["action step acted"]);
});

test("a step that acts waits for the document to be ready; a step that observes does not", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    document.body.setAttribute("is-ready", "false");
    after(() => document.body.removeAttribute("is-ready"));

    tourRegistry.add("tour_act_when_ready", {
        steps: () => [
            {
                trigger: ".button0",
            },
            {
                trigger: ".button1",
                run() {
                    expect.step("action step acted");
                },
            },
        ],
    });

    await odoo.startTour("tour_act_when_ready", { mode: "auto" });
    await animationFrame();
    await animationFrame();
    expect(tourState.getCurrentIndex()).toBe(1);
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect.verifySteps([]);

    document.body.setAttribute("is-ready", "true");
    await waitForMacro();
    expect.verifySteps(["action step acted"]);
});

test("a tour succeeds only once the client is idle", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    patchWithCleanup(browser.console, {
        log: (message) => {
            if (message === "tour succeeded") {
                expect.step(message);
            }
        },
    });

    const pending = { data: { id: 778 }, url: "/web/dataset/call_kw/x/web_save" };
    tourRegistry.add("tour_end_settles", {
        steps: () => [
            {
                trigger: ".button0",
                run() {
                    rpcBus.trigger(RpcEvent.REQUEST, pending);
                },
            },
            {
                trigger: ".button1",
            },
        ],
    });

    await odoo.startTour("tour_end_settles", { mode: "auto" });
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect(tourState.getCurrentIndex()).toBe(2);
    expect.verifySteps([]);

    rpcBus.trigger(RpcEvent.RESPONSE, pending);
    await waitForMacro();
    expect.verifySteps(["tour succeeded"]);
});

test("a step that expects the page to unload does not wait for the client to settle", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
            <t>
                <button class="button0">Button 0</button>
                <button class="button1">Button 1</button>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);

    const pending = { data: { id: 778 }, url: "/website/configurator/apply" };
    tourRegistry.add("tour_unload_no_settle", {
        steps: () => [
            {
                trigger: ".button0",
                run() {
                    rpcBus.trigger(RpcEvent.REQUEST, pending);
                },
            },
            {
                trigger: ".button1",
                expectUnloadPage: true,
                run() {
                    expect.step("unload step acted");
                },
            },
        ],
    });

    await odoo.startTour("tour_unload_no_settle", { mode: "auto" });
    for (let i = 0; i < 5; i++) {
        await animationFrame();
        await advanceTime(265);
    }
    expect.verifySteps(["unload step acted"]);
    rpcBus.trigger(RpcEvent.RESPONSE, pending);
});

test("a request that never answers costs the settle budget once, not per step", async () => {
    const tour = new TourAutomatic({ name: "t", steps: [] });
    tour.pendingRPCs.add(1);

    const first = tour.whenClientSettles(500);
    await advanceTime(600);
    expect(await first).toBe(false);
    expect(tour.pendingRPCs.size).toBe(0);

    expect(await tour.whenClientSettles(500)).toBe(true);
});

test("the settle wait ends as soon as the pending request answers", async () => {
    const tour = new TourAutomatic({ name: "t", steps: [] });
    tour.pendingRPCs.add(7);
    const settling = tour.whenClientSettles(10000);

    tour.pendingRPCs.delete(7);
    rpcBus.trigger(RpcEvent.RESPONSE, { data: { id: 7 }, url: "/answered" });
    await animationFrame();

    expect(await settling).toBe(true);
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
    await odoo.startTour("tour_invalid_trigger", { mode: "auto" });
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
            s = s.replace(/\n +at.*/g, "");
            expect.step(`error: ${s}`);
        },
    });
    class Root extends Component {
        static components = {};
        static template = xml`
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
    await odoo.startTour("tour2", { mode: "auto" });
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
        static template = xml`
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
        static template = xml`
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

test("a tour action can be contributed through the web_tour.helpers registry", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`<t><button class="button0">Button 0</button></t>`;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    const helpers = registry.category("web_tour.helpers");
    clearRegistry(helpers);
    helpers.add("shout", async function (argument) {
        expect.step(`shout:${argument}:${this.anchor.className}`);
    });
    registry.category("web_tour.tours").add("registry_action_tour", {
        steps: () => [{ trigger: ".button0", run: "shout hello" }],
    });
    await odoo.startTour("registry_action_tour", { mode: "auto" });
    await waitForMacro();
    expect.verifySteps(["shout:hello:button0"]);
});

test("a built-in TourHelpers action wins over a registry entry of the same name", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`<t><button class="button0">Button 0</button></t>`;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    const helpers = registry.category("web_tour.helpers");
    clearRegistry(helpers);
    helpers.add("click", async function () {
        expect.step("registry click must not shadow the built-in one");
    });
    registry.category("web_tour.tours").add("shadow_tour", {
        steps: () => [
            { trigger: ".button0", run: "click" },
            { trigger: ".button0", run: () => expect.step("built-in click ran") },
        ],
    });
    await odoo.startTour("shadow_tour", { mode: "auto" });
    await waitForMacro();
    expect.verifySteps(["built-in click ran"]);
});

test("an unknown tour action names the registry in its error", async () => {
    patchWithCleanup(browser.console, {
        groupCollapsed: () => {},
        log: () => {},
        warn: () => {},
        error: (msg) =>
            expect.step(
                String(msg).includes("web_tour.helpers")
                    ? "names the registry"
                    : "unhelpful error",
            ),
    });
    class Root extends Component {
        static components = {};
        static template = xml`<t><button class="button0">Button 0</button></t>`;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    clearRegistry(registry.category("web_tour.helpers"));
    tourRegistry.add("unknown_action_tour", {
        steps: () => [{ trigger: ".button0", run: "definitelynotanaction" }],
    });
    await odoo.startTour("unknown_action_tour", { mode: "auto" });
    await waitForMacro();
    expect.verifySteps(["names the registry"]);
});

test("check tour with inactive steps", async () => {
    class Root extends Component {
        static components = {};
        static template = xml`
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
        static template = xml`
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
        static template = xml`
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
        static template = xml`
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
        static template = xml`
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
        static template = xml`
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

test("the error silencing a finished tour installs is dropped when the next tour starts", async () => {
    // `end()` silences `error`/`unhandledrejection` on purpose: the tour has
    // reported its result and an error the page raises afterwards belongs to
    // nobody. What was not on purpose is that the pair was installed as two
    // inline arrows and never removed -- nothing held a reference to remove.
    // Every finished tour left another capturing pair behind, each calling
    // `stopImmediatePropagation()`, so the NEXT tour in the same page ran with
    // its errors already eaten, and any handler registered after a finished
    // tour could have its own detection eaten too. 15 of the tests in this
    // very file run an auto tour, in one page, with no reload between them.
    //
    // Tracked by listener identity, not by counting: the page registers and
    // drops `error` listeners of its own during a test, so a count says
    // nothing about whose listener it was.
    const calls = [];
    const nativeAdd = window.addEventListener.bind(window);
    const nativeRemove = window.removeEventListener.bind(window);
    const isTracked = (type) => type === "error" || type === "unhandledrejection";
    patchWithCleanup(window, {
        addEventListener(type, listener, options) {
            if (isTracked(type)) {
                calls.push({ op: "add", type, listener });
            }
            return nativeAdd(type, listener, options);
        },
        removeEventListener(type, listener, options) {
            if (isTracked(type)) {
                calls.push({ op: "remove", type, listener });
            }
            return nativeRemove(type, listener, options);
        },
    });
    const lastInstalledPair = () => calls.filter((call) => call.op === "add").slice(-2);
    // Scoped to the calls made after `mark`: an earlier test in this page has
    // already been through an install/remove cycle of the very same pair (the
    // silencing is page-scoped, which is the point), so an unscoped search
    // answers "removed" before this test has removed anything.
    const removedSince = (mark, { type, listener }) =>
        calls
            .slice(mark)
            .some(
                (call) =>
                    call.op === "remove" &&
                    call.type === type &&
                    call.listener === listener,
            );

    class Root extends Component {
        static components = {};
        static template = xml /*html*/ `<t><button class="button0">Button 0</button></t>`;
        static props = ["*"];
    }
    await mountWithCleanup(Root);

    const steps = () => [{ trigger: ".button0", run: "click" }];
    tourRegistry.add("silencer_tour_1", { steps });
    tourRegistry.add("silencer_tour_2", { steps });

    await odoo.startTour("silencer_tour_1", { mode: "auto" });
    await waitForMacro();
    const firstPair = lastInstalledPair();
    expect(firstPair.map(({ type }) => type)).toEqual(["error", "unhandledrejection"]);
    const installed = calls.length;
    expect(firstPair.map((entry) => removedSince(installed, entry))).toEqual([
        false,
        false,
    ]);

    await odoo.startTour("silencer_tour_2", { mode: "auto" });
    // The assertion that bites: before the fix nothing was ever removed and
    // the second tour ran behind the first one's listeners.
    expect(firstPair.map((entry) => removedSince(installed, entry))).toEqual([
        true,
        true,
    ]);

    await waitForMacro();
    // Silencing is back on now that this tour is over too -- with the SAME
    // pair, which is what makes it removable. Two inline arrows would be two
    // new references here, and the page would now carry two pairs.
    const secondPair = lastInstalledPair();
    expect(secondPair.map(({ listener }) => listener)).toEqual(
        firstPair.map(({ listener }) => listener),
    );
});
