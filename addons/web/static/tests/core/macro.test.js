// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    edit,
    queryOne,
    queryText,
} from "@odoo/hoot-dom";
import { advanceFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Macro, MacroMutationObserver, waitUntil } from "@web/core/utils/macro";

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
            const started = super.start(...arguments);
            macro = this;
            return started;
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
    static props = ["*"];
    setup() {
        this.state = useState({ value: 0 });
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
    advanceTime(500);
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

test("macro without onError falls back to a console.error default", async () => {
    patchWithCleanup(console, {
        error: (message, step, index) => expect.step(`${message} @${index}`),
    });
    new Macro({
        name: "test",
        timeout: 1000,
        steps: [{ trigger: ".does-not-exist" }],
    }).start();
    await waitForMacro();
    expect.verifySteps(["TIMEOUT step failed to complete within 1000 ms. @0"]);
});

test("subclass prototype onError receives { error, step, index }", async () => {
    class SubMacro extends Macro {
        onError({ error, step, index }) {
            expect.step(`${error.message} @${index} trigger:${step.trigger}`);
        }
    }
    new SubMacro({
        name: "test",
        timeout: 1000,
        steps: [{ trigger: ".does-not-exist" }],
    }).start();
    await waitForMacro();
    expect.verifySteps([
        "TIMEOUT step failed to complete within 1000 ms. @0 trigger:.does-not-exist",
    ]);
});

test("descriptor onError wins over the default and a subclass prototype onError", async () => {
    patchWithCleanup(console, {
        error: () => expect.step("console.error (default onError)"),
    });
    class SubMacro extends Macro {
        onError() {
            expect.step("prototype onError");
        }
    }
    new SubMacro({
        name: "test",
        timeout: 1000,
        steps: [{ trigger: ".does-not-exist" }],
        onError: ({ error }) => expect.step(`descriptor onError: ${error.message}`),
    }).start();
    await waitForMacro();
    expect.verifySteps([
        "descriptor onError: TIMEOUT step failed to complete within 1000 ms.",
    ]);
});

test("macro clears the step timeout timer once the step settles", async () => {
    await mountWithCleanup(TestComponent);
    let stepControllerAborts = 0;
    patchWithCleanup(AbortController.prototype, {
        abort() {
            if (macro && this === macro.abortController) {
                stepControllerAborts++;
            }
            return super.abort(...arguments);
        },
    });
    new Macro({
        name: "test",
        timeout: 1234,
        steps: [
            {
                trigger: "button.inc",
                action: (el) => el.click(),
            },
        ],
    }).start();
    await waitForMacro();
    expect(queryOne("span.value")).toHaveText("1");
    expect(stepControllerAborts).toBe(1);
    await runAllTimers();
    expect(stepControllerAborts).toBe(1);
});

test("a string action fails fast at construction", async () => {
    expect(
        () =>
            new Macro({
                name: "test",
                // @ts-expect-error
                steps: [{ action: "doStuff" }],
            }),
    ).toThrow(/Error in schema for Macro/);
});

test("Macro.STOP halts the macro without onComplete or onError", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");
    new Macro({
        name: "test",
        steps: [
            { action: () => Macro.STOP },
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
        onComplete: () => expect.step("onComplete"),
        onError: () => expect.step("onError"),
    }).start();
    await waitForMacro();
    expect(span).toHaveText("0");
    expect.verifySteps([]);
});

test("waitUntil rejects when the predicate throws inside the rAF loop", async () => {
    let n = 0;
    const prom = waitUntil(() => {
        n++;
        if (n >= 2) {
            throw new Error("predicate boom");
        }
        return false;
    });
    /** @type {Error} */
    let caught;
    const settled = prom.catch((error) => (caught = error));
    await runAllTimers();
    await settled;
    expect(caught).toBeInstanceOf(Error);
    expect(caught.message).toBe("predicate boom");
});

test("a long macro runs every step without nesting a frame per step", async () => {
    const seen = [];
    const steps = [];
    for (let i = 0; i < 300; i++) {
        steps.push({
            action: () => {
                seen.push(i);
            },
        });
    }
    new Macro({ steps }).start();
    await waitForMacro();
    expect(macro.isComplete).toBe(true);
    expect(seen.length).toBe(300);
    expect(seen[0]).toBe(0);
    expect(seen.at(-1)).toBe(299);
});

test("stop() from a mid-macro step halts the remaining steps", async () => {
    const seen = [];
    new Macro({
        steps: [
            {
                action: () => {
                    seen.push("a");
                },
            },
            {
                action: () => {
                    seen.push("b");
                    return Macro.STOP;
                },
            },
            {
                action: () => {
                    seen.push("c");
                },
            },
        ],
    }).start();
    await waitForMacro();
    expect(seen).toEqual(["a", "b"]);
    expect(macro.isComplete).toBe(true);
});

test("waitUntil removes its abort listener when it settles normally", async () => {
    const controller = new AbortController();
    const { signal } = controller;
    let added = 0;
    let removed = 0;
    const originalAdd = signal.addEventListener.bind(signal);
    const originalRemove = signal.removeEventListener.bind(signal);
    patchWithCleanup(signal, {
        addEventListener(type, listener, options) {
            added++;
            return originalAdd(type, listener, options);
        },
        removeEventListener(type, listener, options) {
            removed++;
            return originalRemove(type, listener, options);
        },
    });
    for (let i = 0; i < 5; i++) {
        let ready = false;
        const prom = waitUntil(() => ready, { signal });
        ready = true;
        advanceFrame();
        await prom;
    }
    expect([added, removed]).toEqual([5, 5], {
        message: "polling one long-lived signal must not accumulate listeners",
    });
});

test("findAllShadowRoots reports roots in document order and skips text nodes", () => {
    const observer = new MacroMutationObserver(() => {});
    const root = document.createElement("div");
    root.append("some text");
    const a = document.createElement("div");
    const b = document.createElement("div");
    root.append(a, b);
    const rootA = a.attachShadow({ mode: "open" });
    const rootB = b.attachShadow({ mode: "open" });
    const nested = document.createElement("div");
    rootA.append(nested);
    const rootNested = nested.attachShadow({ mode: "open" });

    expect(observer.findAllShadowRoots(root)).toEqual([rootA, rootNested, rootB]);
    expect(observer.findAllShadowRoots(document.createTextNode("x"))).toEqual([]);
});
