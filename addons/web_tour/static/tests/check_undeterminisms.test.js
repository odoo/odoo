/** @odoo-module **/

import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { advanceTime, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Macro } from "@web/core/macro";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");

const mainErrorMessage = (trigger) =>
    `ERROR during perform action:\nPotential non deterministic behavior found in 3000ms for trigger ${trigger}.`;

let macro;
const addElement = document.createElement("div");
addElement.classList.add("brol");
addElement.textContent = "Hello world !";

async function waitForSteps(step, callback) {
    await advanceTime(10);
    await advanceTime(500);
    expect.verifySteps(["log: [1/4] Tour tour_to_check_undeterminisms → Step .button0"]);
    if (step > 1) {
        await advanceTime(3001);
        await advanceTime(10);
        await advanceTime(500);
        expect.verifySteps(["log: [2/4] Tour tour_to_check_undeterminisms → Step .button1"]);
    }
    if (step > 2) {
        await advanceTime(3001);
        await advanceTime(10);
        await advanceTime(500);
        expect.verifySteps(["log: [3/4] Tour tour_to_check_undeterminisms → Step .container"]);
    }
    await callback();
    await advanceTime(1500);
    await advanceTime(10000);
}

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

registry.category("web_tour.tours").add("tour_to_check_undeterminisms", {
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
            trigger: ".container",
        },
        {
            trigger: ".button2",
            run: "click",
        },
    ],
});

beforeEach(async () => {
    patchWithCleanup(Macro.prototype, {
        start() {
            super.start(...arguments);
            macro = this;
        },
    });
    patchWithCleanup(browser.console, {
        log: (s) => expect.step(`log: ${s}`),
        error: (s) => expect.step(`error: ${s}`),
        warn: () => {},
        dir: () => {},
    });
    await mountWithCleanup(Root);
    await odoo.startTour("tour_to_check_undeterminisms", {
        mode: "auto",
        delayToCheckUndeterminisms: 3000,
    });
});

afterEach(async () => {
    macro.stop();
    //Necessary in this case because the tours do not do
    //synchronous setTimeouts one after the other.
    await runAllTimers();
});

test("element is no longer visible", async () => {
    await waitForSteps(2, async () => {
        await advanceTime(1000);
        queryFirst(".container").classList.add("d-none");
    });
    const expectedError = `Initial element is no longer visible`;
    expect.verifySteps([
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
${expectedError}`,
    ]);
});

test("change text", async () => {
    await waitForSteps(2, async () => {
        await advanceTime(1000);
        queryFirst(".button1").textContent = "Text has changed :)";
    });
    expect.verifySteps([
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
Initial element has changed:
{
  "node": "<button class=\\"button1\\">Text has changed :)</button>",
  "modifiedText": [
    {
      "before": "Button 1",
      "after": "Text has changed :)"
    }
  ]
}`,
    ]);
});

test("change attributes", async () => {
    await waitForSteps(2, async () => {
        await advanceTime(1000);
        const button1 = queryFirst(".button1");
        button1.classList.add("brol");
        button1.classList.remove("button1");
        button1.setAttribute("data-value", "42");
    });
    const expectedError = `{
  "node": "<button class=\\"brol\\" data-value=\\"42\\">Button 1</button>",
  "modifiedAttributes": [
    {
      "attributeName": "class",
      "before": "button1",
      "after": "brol"
    },
    {
      "attributeName": "data-value",
      "before": null,
      "after": "42"
    }
  ]
}`;
    expect.verifySteps([
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
Initial element has changed:
${expectedError}`,
    ]);
});

test("add child node", async () => {
    await waitForSteps(3, async () => {
        await advanceTime(1000);
        queryFirst(".container").appendChild(addElement);
    });
    const expectedError = `{
  "node": "<div class=\\"container\\"><button class=\\"button0\\">Button 0</button><button class=\\"button1\\">Button 1</button><button class=\\"button2\\">Button 2</button><div class=\\"brol\\">Hello world !</div></div>",
  "modifiedText": [
    {
      "before": "Button 0Button 1Button 2",
      "after": "Button 0Button 1Button 2Hello world !"
    }
  ],
  "addedNodes": [
    {
      "newNode": "<div class=\\"brol\\">Hello world !</div>"
    }
  ]
}`;
    expect.verifySteps([
        `error: FAILED: [3/4] Tour tour_to_check_undeterminisms → Step .container.
${mainErrorMessage(".container")}
Initial element has changed:
${expectedError}`,
    ]);
});

test("snapshot is the same but has mutated", async () => {
    await waitForSteps(2, async () => {
        const button1 = queryFirst(".button1");
        await advanceTime(500);
        button1.setAttribute("data-value", "42");
        await advanceTime(300);
        button1.classList.add("brol");
        button1.removeAttribute("data-value");
        await advanceTime(200);
        button1.classList.remove("brol");
    });
    const expectedError = `Initial element has mutated 4 times:
[
  "attribute: data-value",
  "attribute: class"
]`;
    expect.verifySteps([
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
${expectedError}`,
    ]);
});
