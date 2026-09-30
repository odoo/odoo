import { beforeEach, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    edit,
    queryOne,
    queryText,
    waitUntil,
} from "@odoo/hoot-dom";
import { Component, proxy, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { Macro } from "@web/core/macro";

let macro;
async function waitForMacro() {
    await waitUntil(() => macro.isComplete, {
        timeout: 5_000,
        message: "waitForMacro: macro did not complete in time",
    });
    await animationFrame();
}

beforeEach(() => {
    patchWithCleanup(Macro.prototype, {
        start() {
            super.start(...arguments);
            macro = this;
        },
    });
});

class TestComponent extends Component {
    static template = xml`
        <div class="counter">
            <p><button class="btn inc" t-on-click="() => this.state.value++">increment</button></p>
            <p><button class="btn dec" t-on-click="() => this.state.value--">decrement</button></p>
            <p><button class="btn double" t-on-click="() => this.state.value = 2*this.state.value">double</button></p>
            <span class="value"><t t-out="this.state.value"/></span>
            <input />
        </div>`;
    setup() {
        this.state = proxy({ value: 0 });
    }
}

test("simple use", async () => {
    await mountWithCleanup(TestComponent);
    new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
        async onStep({ trigger }) {
            await animationFrame();
            expect.step(queryText("span.value"));
        },
    }).start();

    const span = queryOne("span.value");
    expect(span).toHaveText("0");
    await waitForMacro();
    expect.verifySteps(["1"]);
});

test("multiple steps", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");

    new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
            {
                trigger: () => (span.textContent === "1" ? span : null),
            },
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
        async onStep({ index }) {
            await animationFrame();
            if (index % 2 === 0) {
                expect.step(queryText("span.value"));
            }
        },
    }).start();
    await waitForMacro();
    expect.verifySteps(["1", "2"]);
});

test("can input values", async () => {
    await mountWithCleanup(TestComponent);
    const input = queryOne("input");
    new Macro({
        name: "test",
        steps: [
            {
                trigger: "div.counter input",
                async action(trigger) {
                    await click(trigger);
                    await edit("aaron", { confirm: "blur" });
                },
            },
        ],
    }).start();
    expect(input).toHaveValue("");
    await waitForMacro();
    expect(input).toHaveValue("aaron");
});

test("a step can have no trigger", async () => {
    await mountWithCleanup(TestComponent);
    const input = queryOne("input");
    new Macro({
        name: "test",
        steps: [
            { action: () => expect.step("1") },
            { action: () => expect.step("2") },
            {
                trigger: "div.counter input",
                async action(trigger) {
                    await click(trigger);
                    await edit("aaron", { confirm: "blur" });
                },
            },
            { action: () => expect.step("3") },
        ],
    }).start();
    expect(input).toHaveValue("");
    await waitForMacro();
    expect(input).toHaveValue("aaron");
    expect.verifySteps(["1", "2", "3"]);
});

test("onStep function is called at each step", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");

    new Macro({
        name: "test",
        onStep: ({ index }) => {
            expect.step(index);
        },
        steps: [
            {
                action: () => {
                    console.log("brol");
                },
            },
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
    }).start();
    await waitForMacro();
    expect(span).toHaveText("1");
    expect.verifySteps([0, 1]);
});

test("trigger can be a function returning an htmlelement", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");

    new Macro({
        name: "test",
        steps: [
            {
                trigger: () => queryOne("button.inc"),
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
    }).start();
    expect(span).toHaveText("0");
    await waitForMacro();
    expect(span).toHaveText("1");
});

test("macro wait element is visible to do action", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    const button = queryOne("button.inc");
    button.classList.add("d-none");
    expect(span).toHaveText("0");
    new Macro({
        name: "test",
        timeout: 1000,
        steps: [
            {
                trigger: "button.inc",
                action: () => {
                    expect.step("element is now visible");
                },
            },
        ],
        onError: (error) => {
            expect.step(error);
        },
    }).start();
    await advanceTime(500);
    button.classList.remove("d-none");
    await waitForMacro();
    expect.verifySteps(["element is now visible"]);
});

test("macro timeout if element is not visible", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    const button = queryOne("button.inc");
    button.classList.add("d-none");
    expect(span).toHaveText("0");
    const macro = new Macro({
        name: "test",
        timeout: 1000,
        steps: [
            {
                trigger: "button.inc",
                action: () => {
                    expect.step("element is now visible");
                },
            },
        ],
        onError: ({ error }) => {
            expect.step(error.message);
        },
    });
    macro.start();
    await waitForMacro();
    expect.verifySteps(["TIMEOUT step failed to complete within 1000 ms."]);
});

test("playing without a step index throws", async () => {
    const macro = new Macro({
        name: "test",
        steps: [{ action: () => expect.step("a") }],
        onError: ({ error }) => expect.step(error.message),
    });
    await expect(macro.play()).rejects.toThrow("Macro.play() expects a step index, got undefined");
    await expect(macro.play(-1)).rejects.toThrow("Macro.play() expects a step index, got -1");
    expect.verifySteps([]);
});

test("playing an index interrupts the step waiting for its trigger", async () => {
    await mountWithCleanup(TestComponent);
    const macro = new Macro({
        name: "test",
        steps: [
            { trigger: "button.never", action: () => expect.step("a") },
            { action: () => expect.step("b") },
            { action: () => expect.step("c") },
        ],
        onComplete: () => expect.step("complete"),
    });
    macro.start();
    await animationFrame();
    expect.verifySteps([]);

    macro.play(2);
    await waitForMacro();
    expect.verifySteps(["c", "complete"]);
});

test("playing an index from a step jumps to it once the step is done", async () => {
    const macro = new Macro({
        name: "test",
        steps: [
            {
                action: () => {
                    expect.step("a");
                    macro.play(2);
                },
            },
            { action: () => expect.step("b") },
            { action: () => expect.step("c") },
        ],
    });
    macro.start();
    await waitForMacro();
    expect.verifySteps(["a", "c"]);
});

test("playing a previous index from a trigger goes back to it", async () => {
    await mountWithCleanup(TestComponent);
    let goneBack = false;
    const macro = new Macro({
        name: "test",
        steps: [
            { action: () => expect.step("a") },
            {
                trigger: () => {
                    if (!goneBack) {
                        goneBack = true;
                        macro.play(0);
                        return false;
                    }
                    return true;
                },
                action: () => expect.step("b"),
            },
        ],
    });
    macro.start();
    await waitForMacro();
    expect.verifySteps(["a", "a", "b"]);
});

test("stopping a macro stops waiting for the trigger", async () => {
    await mountWithCleanup(TestComponent);
    const macro = new Macro({
        name: "test",
        steps: [
            {
                trigger: () => {
                    expect.step("check");
                    return false;
                },
            },
        ],
        onComplete: () => expect.step("complete"),
    });
    macro.start();
    await animationFrame();
    macro.stop();
    expect.verifySteps(["check", "check"]);
    await animationFrame();
    await animationFrame();
    expect.verifySteps([]);
});

test("a step with an infinite timeout never times out", async () => {
    await mountWithCleanup(TestComponent);
    const button = queryOne("button.inc");
    button.classList.add("d-none");
    new Macro({
        name: "test",
        timeout: Infinity,
        steps: [{ trigger: "button.inc", action: () => expect.step("visible") }],
        onError: ({ error }) => expect.step(error.message),
    }).start();
    await advanceTime(100_000);
    expect.verifySteps([]);
    button.classList.remove("d-none");
    await waitForMacro();
    expect.verifySteps(["visible"]);
});
