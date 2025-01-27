import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Macro } from "@web/core/macro";

async function waitForStep(first = false) {
    await advanceTime(10);
    await advanceTime(500);
    if (!first) {
        await advanceTime(50);
    }
}

class TestComponent extends Component {
    static template = xml`
        <div class="counter">
            <p><button class="btn inc" t-on-click="() => this.state.value++">increment</button></p>
            <p><button class="btn dec" t-on-click="() => this.state.value--">decrement</button></p>
            <p><button class="btn double" t-on-click="() => this.state.value = 2*this.state.value">double</button></p>
            <span class="value"><t t-esc="state.value"/></span>
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
                action: "click",
            },
        ],
    }).start(queryOne(".counter"));

    const span = queryOne("span.value");
    expect(span).toHaveText("0");
    await waitForStep(true);
    expect(span).toHaveText("1");
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
                action: "click",
            },
            {
                trigger: () => {
                    return span.textContent === "1" ? span : null;
                },
            },
            {
                trigger: "button.inc",
                action: "click",
            },
        ],
    }).start(queryOne(".counter"));
    await waitForStep(true);
    expect(span).toHaveText("1");
    await waitForStep();
    expect(span).toHaveText("2");
    await waitForStep();
    expect(span).toHaveText("2");
});

test("can use a function as action", async () => {
    await mountWithCleanup(TestComponent);
    let flag = false;
    new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                action: () => {
                    flag = true;
                },
            },
        ],
    }).start(queryOne(".counter"));
    expect(flag).toBe(false);
    await waitForStep(true);
    expect(flag).toBe(true);
});

test("can input values", async () => {
    await mountWithCleanup(TestComponent);
    const input = queryOne("input");
    new Macro({
        name: "test",
        steps: [
            {
                trigger: "div.counter input",
                action: "text",
                value: "aaron",
            },
        ],
    }).start(queryOne(".counter"));
    expect(input).toHaveValue("");
    await waitForStep(true);
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
                action: "text",
                value: "aaron",
            },
            { action: () => expect.step("3") },
        ],
    }).start(queryOne(".counter"));
    expect(input).toHaveValue("");
    await waitForStep(true);
    await waitForStep();
    await waitForStep();
    expect(input).toHaveValue("aaron");
    await waitForStep();
    expect.verifySteps(["1", "2", "3"]);
});

test("onStep function is called at each step", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");

    new Macro({
        name: "test",
        onStep: (el, step) => {
            expect.step(step.info);
        },
        steps: [
            { info: "1" },
            {
                info: "2",
                trigger: "button.inc",
                action: "click",
            },
        ],
    }).start(queryOne(".counter"));
    await waitForStep(true);
    expect(span).toHaveText("1");
    expect.verifySteps(["1", "2"]);
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
                action: "click",
            },
        ],
    }).start(queryOne(".counter"));
    expect(span).toHaveText("0");
    await waitForStep(true);
    expect(span).toHaveText("1");
});

test("macro does not click on invisible element", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    const button = queryOne("button.inc");
    expect(span).toHaveText("0");

    new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                action: "click",
            },
        ],
    }).start(queryOne(".counter"));
    button.classList.add("d-none");
    await animationFrame(); // let mutation observer trigger
    await advanceTime(100);
    expect(span).toHaveText("0");
    await advanceTime(100);
    expect(span).toHaveText("0");
    button.classList.remove("d-none");
    await animationFrame(); // let mutation observer trigger
    await advanceTime(500);
    await advanceTime(500);
    expect(span).toHaveText("1");
});
