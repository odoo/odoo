import { expect, test } from "@odoo/hoot";
import { click, edit, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Macro } from "@web/core/macro";

async function macroIsComplete(macro) {
    while (!macro.isComplete) {
        await animationFrame();
    }
}

function onTextChange(element, callback) {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.type === "characterData" || mutation.type === "childList") {
                callback(element.textContent);
            }
        }
    });
    observer.observe(element, {
        characterData: true,
        childList: true,
        subtree: true,
    });
    return observer;
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
    const span = queryOne("span.value");
    const macro = new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
    });
    macro.start(queryOne(".counter"));
    onTextChange(span, expect.step);
    await macroIsComplete(macro);
    expect.verifySteps(["1"]);
});

test("multiple steps", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");
    const macro = new Macro({
        name: "test",
        steps: [
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
            {
                trigger: () => {
                    return span.textContent === "1" ? span : null;
                },
            },
            {
                trigger: "button.inc",
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
    });
    macro.start(queryOne(".counter"));
    onTextChange(span, expect.step);
    await macroIsComplete(macro);
    expect.verifySteps(["1", "2"]);
});

test("can input values", async () => {
    await mountWithCleanup(TestComponent);
    const input = queryOne("input");
    const macro = new Macro({
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
    });
    macro.start(queryOne(".counter"));
    expect(input).toHaveValue("");
    await macroIsComplete(macro);
    expect(input).toHaveValue("aaron");
});

test("a step can have no trigger", async () => {
    await mountWithCleanup(TestComponent);
    const input = queryOne("input");
    const macro = new Macro({
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
    });
    macro.start(queryOne(".counter"));
    expect(input).toHaveValue("");
    await macroIsComplete(macro);
    expect(input).toHaveValue("aaron");
    expect.verifySteps(["1", "2", "3"]);
});

test("trigger can be a function returning an htmlelement", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    expect(span).toHaveText("0");
    const macro = new Macro({
        name: "test",
        steps: [
            {
                trigger: () => queryOne("button.inc"),
                async action(trigger) {
                    await click(trigger);
                },
            },
        ],
    });
    macro.start(queryOne(".counter"));
    expect(span).toHaveText("0");
    await macroIsComplete(macro);
    expect(span).toHaveText("1");
});

test("macro wait element is visible to do action", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    const button = queryOne("button.inc");
    expect(span).toHaveText("0");
    button.classList.add("d-none");
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
        onError: (error) => {
            expect.step(error);
        },
    });
    macro.start(queryOne(".counter"));
    setTimeout(() => {
        button.classList.remove("d-none");
    }, 500);
    await macroIsComplete(macro);
    expect.verifySteps(["element is now visible"]);
});

test("macro timeout if element is not visible", async () => {
    await mountWithCleanup(TestComponent);
    const span = queryOne("span.value");
    const button = queryOne("button.inc");
    expect(span).toHaveText("0");
    button.classList.add("d-none");
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
        onError: (error) => {
            expect.step(error.message);
        },
    });
    macro.start(queryOne(".counter"));
    setTimeout(() => {
        button.classList.remove("d-none");
    }, 1500);
    await macroIsComplete(macro);
    expect.verifySteps(["1000"]);
});
