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
