/** @odoo-module **/

import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Macro } from "@web/core/macro";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");

const mainErrorMessage = (trigger) =>
    `Error: Potential non deterministic behavior found in 300ms for trigger ${trigger}.`;

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
        error: (s) => {
            s = s.replace(/\n +at.*/g, ""); // strip stack trace
            expect.step(`error: ${s}`);
        },
        warn: () => {},
        dir: () => {},
    });
    await mountWithCleanup(Root);
    await odoo.startTour("tour_to_check_undeterminisms", {
        mode: "auto",
        delayToCheckUndeterminisms: 300,
    });
});

afterEach(() => {
    macro.stop();
});

test("element is no longer visible", async () => {
    macro.onStep = ({ index }) => {
        if (index == 2) {
            setTimeout(() => {
                queryFirst(".container").classList.add("d-none");
            }, 400);
        }
    };
    await waitForMacro();
    const expectedError = `Initial element is no longer visible`;
    expect.verifySteps([
        "log: [1/4] Tour tour_to_check_undeterminisms → Step .button0",
        "log: [2/4] Tour tour_to_check_undeterminisms → Step .button1",
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
${expectedError}`,
    ]);
});

test("change text", async () => {
    macro.onStep = ({ index }) => {
        if (index == 2) {
            setTimeout(() => {
                queryFirst(".button1").textContent = "Text has changed :)";
            }, 400);
        }
    };
    await waitForMacro();
    expect.verifySteps([
        "log: [1/4] Tour tour_to_check_undeterminisms → Step .button0",
        "log: [2/4] Tour tour_to_check_undeterminisms → Step .button1",
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
    macro.onStep = ({ index }) => {
        if (index == 2) {
            setTimeout(() => {
                const button1 = queryFirst(".button1");
                button1.classList.add("brol");
                button1.classList.remove("button1");
                button1.setAttribute("data-value", "42");
            }, 400);
        }
    };
    await waitForMacro();
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
        "log: [1/4] Tour tour_to_check_undeterminisms → Step .button0",
        "log: [2/4] Tour tour_to_check_undeterminisms → Step .button1",
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
Initial element has changed:
${expectedError}`,
    ]);
});

test("add child node", async () => {
    macro.onStep = ({ index }) => {
        if (index == 4) {
            setTimeout(() => {
                const addElement = document.createElement("div");
                addElement.classList.add("brol");
                addElement.textContent = "Hello world !";
                queryFirst(".container").appendChild(addElement);
            }, 400);
        }
    };
    await waitForMacro();
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
        "log: [1/4] Tour tour_to_check_undeterminisms → Step .button0",
        "log: [2/4] Tour tour_to_check_undeterminisms → Step .button1",
        "log: [3/4] Tour tour_to_check_undeterminisms → Step .container",
        `error: FAILED: [3/4] Tour tour_to_check_undeterminisms → Step .container.
${mainErrorMessage(".container")}
Initial element has changed:
${expectedError}`,
    ]);
});

test.skip("snapshot is the same but has mutated", async () => {
    macro.onStep = async ({ index }) => {
        if (index === 2) {
            setTimeout(() => {
                const button1 = queryFirst(".button1");
                button1.setAttribute("data-value", "42");
                button1.classList.add("brol");
                button1.removeAttribute("data-value");
                button1.classList.remove("brol");
            }, 400);
        }
    };
    await waitForMacro();
    const expectedError = `Initial element has mutated 4 times:
[
  "attribute: data-value",
  "attribute: class"
]`;
    expect.verifySteps([
        "log: [1/4] Tour tour_to_check_undeterminisms → Step .button0",
        "log: [2/4] Tour tour_to_check_undeterminisms → Step .button1",
        `error: FAILED: [2/4] Tour tour_to_check_undeterminisms → Step .button1.
${mainErrorMessage(".button1")}
${expectedError}`,
    ]);
});
