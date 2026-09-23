// @ts-check

import { before, beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    dblclick,
    freezeTime,
    queryAll,
    queryFirst,
    queryOne,
} from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { Component, markup, onWillDestroy, xml } from "@odoo/owl";
import { clearRegistry, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { Colibri } from "@web/public/colibri";
import { Interaction } from "@web/public/interaction";
import { InteractionService } from "@web/public/interaction_service";
import { patchDynamicContent } from "@web/public/utils";

import { getInteraction, startInteraction, startInteractions } from "./helpers.js";

describe.current.tags("interaction_dev");

async function startInteractionsCounted(Is, html) {
    let scanCount = 0;
    patchWithCleanup(InteractionService.prototype, {
        startInteractions(target) {
            scanCount++;
            return super.startInteractions(target);
        },
    });
    const { core } = await startInteraction(Is, html);
    return { core: Object.assign(core, { scanCount: scanCount - 1 }) };
}

const TemplateBase = `
    <div>
        <span>coucou</span>
    </div>`;

const TemplateTest = `
    <div class="test">
        <span>coucou</span>
    </div>`;

const TemplateTestDoubleSpan = `
    <div class="test">
        <span>span1</span>
        <span>span2</span>
    </div>`;

const TemplateTestDoubleButton = `
    <div class="test">
        <button>button1</button>
        <button>button2</button>
    </div>`;

const getTemplateWithAttribute = function (attribute) {
    return `
    <div>
        <span ${attribute}">coucou</span>
    </div>`;
};

function installProtect() {
    patchWithCleanup(Colibri.prototype, {
        updateContent() {
            expect.step("updateContent");
            super.updateContent();
        },
        bindDeferred(interaction, fn) {
            fn = super.bindDeferred(interaction, fn);
            return (...args) => {
                expect.step("protect");
                fn(...args);
                expect.step("unprotect");
            };
        },
    });
}

describe("adding listeners", () => {
    test("can add a listener on a single element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click("span");
        expect(clicked).toBe(1);
    });

    test("can add a listener on multiple elements", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTestDoubleSpan);
        expect(clicked).toBe(0);
        const spans = queryAll("span");
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
    });

    test.tags("desktop");
    test("can add multiple listeners on an element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": () => clicked++,
                    "t-on-dblclick": () => clicked++,
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await dblclick("span");
        expect(clicked).toBe(3);
    });

    test("can use addListener on HTMLCollection", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.addListener(
                    this.el.querySelectorAll("span"),
                    "click",
                    () => clicked++,
                );
            }
        }
        await startInteraction(Test, TemplateTestDoubleSpan);
        expect(clicked).toBe(0);
        const spans = queryAll("span");
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
    });

    test("listener is added between willstart and start", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click": () => expect.step("click") },
            };
            setup() {
                expect.step("setup");
            }
            async willStart() {
                await click("span");
                expect.step("willStart");
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(Test, TemplateTest);
        await click("span");
        expect.verifySteps(["setup", "willStart", "start", "click"]);
    });

    test("listener is added on iframe single element", async () => {
        class Test extends Interaction {
            static selector = "iframe";
            start() {
                const doc = /** @type {Document} */ (
                    /** @type {HTMLIFrameElement} */ (this.el).contentDocument
                );
                const spanEl = doc.createElement("span");
                spanEl.textContent = "abc";
                doc.body.appendChild(spanEl);
                this.addListener(spanEl, "click", () => expect.step("click"));
                spanEl.click();
            }
        }
        await startInteraction(Test, `<iframe src="about:blank"/>`);
        expect.verifySteps(["click"]);
    });

    test("listener is added on iframe elements", async () => {
        class Test extends Interaction {
            static selector = "iframe";
            start() {
                const doc = /** @type {Document} */ (
                    /** @type {HTMLIFrameElement} */ (this.el).contentDocument
                );
                const spanEl = doc.createElement("span");
                spanEl.textContent = "abc";
                doc.body.appendChild(spanEl);
                const spanEls = /** @type {HTMLIFrameElement} */ (
                    this.el
                ).contentDocument.querySelectorAll("span");
                this.addListener(spanEls, "click", () => expect.step("click"));
                spanEl.click();
            }
        }
        await startInteraction(Test, `<iframe src="about:blank"/>`);
        expect.verifySteps(["click"]);
    });
    test("updateContent after async listener", async () => {
        const def = new Deferred();
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": async () => {
                        await def;
                        clicked++;
                    },
                    "t-att-x": () => clicked.toString(),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        await click("span");
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        def.resolve();
        await animationFrame();
        expect(clicked).toBe(1);
        expect("span").toHaveAttribute("x", "1");
    });
});

describe("using selectors", () => {
    test("can add a listener on root element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click(".test");
        expect(clicked).toBe(1);
    });

    test("can add a listener on body element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _body: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click(document.body);
        expect(clicked).toBe(1);
    });

    test("can add a listener on window element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _window: { "t-on-event": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await window.dispatchEvent(new Event("event"));
        expect(clicked).toBe(1);
    });

    test("can add a listener on document ", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _document: { "t-on-event": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await window.document.dispatchEvent(new Event("event"));
        expect(clicked).toBe(1);
    });

    test("can add a listener on modal element, if any", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                _modal: () => this.el.closest(".modal"),
            };
            dynamicContent = {
                _modal: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, `<div class="modal">${TemplateTest}</div>`);
        expect(clicked).toBe(0);
        await click(".modal");
        expect(clicked).toBe(1);
    });

    test("can refresh nodes", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".me": {
                    "t-on-click": (ev) => {
                        clicked++;
                        ev.currentTarget.parentElement
                            .querySelectorAll("span:not(.me)")
                            .forEach((el) => el.classList.add("me"));
                        ev.currentTarget.classList.remove("me");
                    },
                },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span class="me">span1</span>
                <span>span2</span>
                <span>span3</span>
            </div>
        `,
        );
        async function clickAll() {
            for (const el of queryAll(".me")) {
                await click(el);
            }
        }
        expect(clicked).toBe(0);
        await clickAll();
        expect(clicked).toBe(1);
        await clickAll();
        expect(clicked).toBe(3);
    });

    test("refreshing nodes prunes departed listener cleanups (no leak)", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".me": {
                    "t-on-click": (ev) => {
                        ev.currentTarget.parentElement
                            .querySelectorAll("span")
                            .forEach((el) => el.classList.toggle("me"));
                    },
                },
            };
        }
        const { core } = await startInteraction(
            Test,
            `
            <div class="test">
                <span class="me">span1</span>
                <span>span2</span>
            </div>
        `,
        );
        const colibri = core.interactions[0];
        const baseline = colibri.cleanups.length;
        for (let i = 0; i < 15; i++) {
            for (const el of queryAll(".me")) {
                await click(el);
            }
        }
        expect(colibri.cleanups.length).toBeLessThan(baseline + 3);
    });

    test("pruning a departed node keeps its other selectors' listeners removable", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".a": { "t-on-click": () => expect.step("a") },
                ".b": { "t-on-click": () => expect.step("b") },
            };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><button class="a b">go</button></div>`,
        );
        await click("button");
        expect.verifySteps(["a", "b"]);

        queryOne("button").classList.remove("a");
        getInteraction(core, Test).updateContent();
        await click("button");
        expect.verifySteps(["b"]);

        core.stopInteractions();
        await click("button");
        expect.verifySteps([]);
    });

    test("does not crash if no modal is found", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                _modal: () => {
                    expect.step("check");
                    return null;
                },
            };
            dynamicContent = {
                _modal: { "t-on-click": () => clicked++ },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["check"]);
        expect(clicked).toBe(0);
    });

    test("allow pseudo-classes in inline format in dynamicContent", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".btn:not(.off)": { "t-on-click": () => expect.step("doStuff") },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span class="btn"></span>
                <span class="btn off"></span>
            </div>`,
        );
        expect.verifySteps([]);
        await click(".btn:not(.off)");
        expect.verifySteps(["doStuff"]);
        await click(".btn.off");
        expect.verifySteps([]);
    });

    test("allow customized special selector", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                _myselector: () => this.el.querySelector(".my-selector"),
            };
            dynamicContent = {
                _myselector: { "t-att-animal": () => "colibri" },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span class="my-selector">coucou</span>
            </div>`,
        );
        expect("span").toHaveAttribute("animal", "colibri");
    });

    test("dynamic selector can return multiple nodes", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                _myselector: () => this.el.querySelectorAll(".my-selector"),
            };
            dynamicContent = {
                _myselector: { "t-att-animal": () => "colibri" },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span class="my-selector">coucou</span>
                <span class="my-selector">coucou</span>
                <span class="my-selector">coucou</span>
            </div>`,
        );
        expect(queryAll("span")).toHaveAttribute("animal", "colibri");
    });

    test("dynamicSelector on form element is applied on form, not on controls", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-att-animal": () => "colibri" },
            };
        }
        await startInteraction(
            Test,
            `
            <form class="test">
                <input type="text">coucou</input>
                <button type="button"/>Submit</button>
            </form>`,
        );
        expect(".test").toHaveAttribute("animal", "colibri");
        expect(".test input").not.toHaveAttribute("animal");
        expect(".test button").not.toHaveAttribute("animal");
    });
});

describe("removing listeners", () => {
    test("listener added with addListener is cleaned up", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.addListener(
                    this.el.querySelector("span"),
                    "click",
                    () => clicked++,
                );
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click("span");
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click("span");
        expect(clicked).toBe(1);
    });

    test("single listener added with addListener can be removed", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.removeListener = this.addListener(
                    this.el.querySelector("span"),
                    "click",
                    () => clicked++,
                );
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click("span");
        expect(clicked).toBe(1);
        getInteraction(core, Test).removeListener();
        await click("span");
        expect(clicked).toBe(1);
    });

    test("multiple listeners added with addListener can be removed", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.removeListener = this.addListener(
                    this.el.querySelectorAll("span"),
                    "click",
                    () => clicked++,
                );
            }
        }
        const { core } = await startInteraction(Test, TemplateTestDoubleSpan);
        expect(clicked).toBe(0);
        const spans = queryAll("span");
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
        getInteraction(core, Test).removeListener();
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
    });

    test("listener is cleaned up when interaction is stopped", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click": () => clicked++ },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click("span");
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click("span");
        expect(clicked).toBe(1);
    });

    test("side effects are cleaned up in reverse order", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => expect.step("click1") },
            };
            setup() {
                expect.step("setup");
                this.el.click();
                this.registerCleanup(() => expect.step("a"));
                this.registerCleanup(() => {
                    expect.step("b");
                    this.el.click();
                });
            }
            start() {
                expect.step("start");
                this.el.click();
                this.registerCleanup(() => {
                    expect.step("c");
                    this.el.click();
                });
                this.addListener(this.el, "click", () => expect.step("click2"));
                this.registerCleanup(() => {
                    expect.step("d");
                    this.el.click();
                });
            }
            destroy() {
                this.el.click();
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect.verifySteps(["setup", "start", "click1"]);
        core.stopInteractions();
        expect.verifySteps(["d", "click1", "click2", "c", "click1", "b", "a"]);
        await click(".test");
        expect.verifySteps([]);
    });
});

describe("handling crashes", () => {
    test("crash if a function is not provided to addListener", async () => {
        class Test extends Interaction {
            static selector = ".test";
            start() {
                expect(() => this.addListener(this.el, "click", null)).toThrow(
                    "Invalid listener for event 'click' (not a function)",
                );
            }
        }
        await startInteraction(Test, TemplateTest);
        await click(".test");
    });

    test("a dynamic selector yielding a non-target names itself in the error", async () => {
        expect.errors(1);
        class Test extends Interaction {
            setup() {
                Object.assign(this.dynamicSelectors, {
                    _bogus: () => "not-a-node",
                });
            }

            static selector = ".test";

            dynamicContent = { _bogus: { "t-on-click": () => {} } };
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "Cannot listen to 'click' on a value that is not an event target (selector '_bogus' in interaction 'Test')",
        );
        await animationFrame();
        expect.verifyErrors([/not an event target/]);
    });

    test("this.addListener crashes if interaction is not started", async () => {
        expect.errors(1);
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.addListener(
                    this.el.querySelector("span"),
                    "click",
                    () => clicked++,
                );
            }
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "this.addListener can only be called after the interaction is started",
        );
        await animationFrame();
        expect.verifyErrors([/can only be called after the interaction is started/]);
    });

    test("cannot update content while updating content", async () => {
        let update = false;
        /** @type {Test} */
        let interaction = null;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-att-a": () => {
                        if (update) {
                            expect(() => interaction.updateContent()).toThrow(
                                "updateContent should not be called while interaction is updating",
                            );
                        }
                        return "a";
                    },
                },
            };
            setup() {
                interaction = this;
            }
        }
        await startInteraction(Test, TemplateTest);
        update = true;
        interaction.updateContent();
    });

    test("recover from a throwing t-out definition", async () => {
        let boom = false;
        /** @type {Test} */
        let interaction = null;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": () => this.count++,
                    "t-att-data-count": () => this.count,
                },
                span: {
                    "t-out": () => {
                        if (boom) {
                            throw new Error("boom");
                        }
                        return `colibri ${this.count}`;
                    },
                },
            };
            setup() {
                this.count = 1;
                interaction = this;
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(".test").toHaveAttribute("data-count", "1");
        expect("span").toHaveText("colibri 1");

        boom = true;
        interaction.count = 5;
        expect(() => interaction.updateContent()).toThrow(
            "An error occured while updating 't-out' content (selector 'span') (in interaction 'Test')",
        );
        expect(".test").toHaveAttribute("data-count", "5");

        boom = false;
        await click(".test");
        expect(".test").toHaveAttribute("data-count", "6");
        expect("span").toHaveText("colibri 6");
    });

    test("a throwing restore step on destroy still removes listeners", async () => {
        let boom = false;
        patchWithCleanup(Colibri.prototype, {
            applyAttr(...args) {
                if (boom) {
                    throw new Error("boom");
                }
                super.applyAttr(...args);
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-att-animal": () => "colibri",
                    "t-on-click.noUpdate": () => expect.step("click"),
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        await click(".test");
        expect.verifySteps(["click"]);

        boom = true;
        expect(() => core.stopInteractions()).toThrow(
            "Could not destroy some interactions",
        );
        boom = false;
        expect(core.interactions).toHaveLength(0);
        await click(".test");
        expect.verifySteps([]);
    });

    test("a throwing event handler reaches the error channel", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": () => {
                        throw new Error("boom");
                    },
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        patchWithCleanup(core, {
            reportError(error) {
                if (!(error instanceof Error)) {
                    throw error;
                }
                expect.step(`reported:${error.message}`);
            },
        });
        await click(".test");
        await animationFrame();
        expect.verifySteps(["reported:boom"]);
    });

    test("a throwing t-att during the implicit update reaches the error channel", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": () => (this.exploded = true),
                    "t-att-animal": () => {
                        if (this.exploded) {
                            throw new Error("boom");
                        }
                        return "colibri";
                    },
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        patchWithCleanup(core, {
            reportError(error) {
                if (!(error instanceof Error)) {
                    throw error;
                }
                expect.step(`reported:${error.message}`);
            },
        });
        await click(".test");
        await animationFrame();
        expect.verifySteps([
            "reported:An error occured while updating dynamic attribute 'animal' (selector '_root') (in interaction 'Test')",
        ]);
    });

    test("dom is updated after event is dispatched", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": () => this.clickCount++,
                    "t-att-data-count": () => this.clickCount,
                },
            };
            setup() {
                this.clickCount = 1;
            }
        }
        await startInteraction(Test, TemplateTest);
        const span = queryOne("span");
        expect(span).toHaveAttribute("data-count", "1");
        await click(span);
        expect(span).toHaveAttribute("data-count", "2");
        await animationFrame();
        expect(span).toHaveAttribute("data-count", "2");
    });

    test("crashes if a dynamic content element does not start with t-", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { click: () => {} },
            };
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "Invalid directive: 'click' (should start with t-)",
        );
        await animationFrame();
        expect.verifyErrors([/Invalid directive: 'click'/]);
    });

    test("crash if dynamicContent is defined on class, not on instance", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            static dynamicContent = {};
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "The dynamic content object should be defined on the instance, not on the class (Test)",
        );
        await animationFrame();
        expect.verifyErrors([
            /dynamic content object should be defined on the instance/,
        ]);
    });

    test("crash if selector is defined on instance, not on class", async () => {
        expect.errors(1);
        class Test extends Interaction {
            selector = ".test";
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "The selector should be defined as a static property on the class Test, not on the instance",
        );
        await animationFrame();
        expect.verifyErrors([/selector should be defined as a static property/]);
    });

    test("crash if first-level key on dynamicContent is a directive, not a selector", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { "t-on-click": () => {} };
        }
        await expect(startInteraction(Test, TemplateTest)).rejects.toThrow(
            "Selector missing for key t-on-click in dynamicContent (interaction 'Test')",
        );
        await animationFrame();
        expect.verifyErrors([/Selector missing for key t-on-click/]);
    });
});

describe("using qualifiers", () => {
    test("add a listener with the .stop qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click.stop": this.doSomething },
            };
            doSomething(ev) {
                clicked = true;
                expect(ev.defaultPrevented).toBe(false);
                expect(ev.cancelBubble).toBe(true);
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
    });

    test("add a listener with the .prevent qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click.prevent": this.doSomething },
            };
            doSomething(ev) {
                clicked = true;
                expect(ev.defaultPrevented).toBe(true);
                expect(ev.cancelBubble).toBe(false);
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
    });

    test("add a listener with the .capture qualifier", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                strong: { "t-on-click": () => expect.step("strong") },
                span: { "t-on-click.capture": () => expect.step("span") },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span>
                    <strong>coucou</strong>
                </span>
            </div>`,
        );
        expect.verifySteps([]);
        await click("strong");
        expect.verifySteps(["span", "strong"]);
    });

    test("add a listener without the .capture qualifier", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                strong: { "t-on-click": () => expect.step("strong") },
                span: { "t-on-click": () => expect.step("span") },
            };
        }
        await startInteraction(
            Test,
            `
            <div class="test">
                <span>
                    <strong>coucou</strong>
                </span>
            </div>`,
        );
        expect.verifySteps([]);
        await click("strong");
        expect.verifySteps(["strong", "span"]);
    });

    test("add a listener with the .once qualifier", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-on-click.once": () => expect.step("span") },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click("span");
        await click("span");
        expect.verifySteps(["span"]);
    });

    test("add a listener with the .noUpdate qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.noUpdate": this.doSomething,
                    "t-att-class": () => ({ a: clicked }),
                },
            };
            doSomething(ev) {
                clicked = true;
                expect(ev.defaultPrevented).toBe(false);
                expect(ev.cancelBubble).toBe(false);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
        expect("span").not.toHaveClass("a");
        getInteraction(core, Test).updateContent();
        expect("span").toHaveClass("a");
    });

    test("add a listener with the .withTarget qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.withTarget": this.doSomething,
                    "t-att-class": () => ({ a: clicked }),
                },
            };
            doSomething(ev, el) {
                clicked = true;
                expect(ev.defaultPrevented).toBe(false);
                expect(ev.cancelBubble).toBe(false);
                expect(el.tagName).toBe("SPAN");
            }
        }

        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
        expect("span").toHaveClass("a");
    });

    test("add a listener with several qualifiers", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.noUpdate.stop.prevent": this.doSomething,
                    "t-att-class": () => ({ a: clicked }),
                },
            };
            doSomething(ev) {
                clicked = true;
                expect(ev.defaultPrevented).toBe(true);
                expect(ev.cancelBubble).toBe(true);
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
        expect("span").not.toHaveClass("a");
        getInteraction(core, Test).updateContent();
        expect("span").toHaveClass("a");
    });

    test("add a listener does not lose 'this' with qualifiers", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.noUpdate.stop.prevent": this.doSomething,
                },
            };
            doSomething(ev) {
                clicked = true;
                expect(this).not.toBe(undefined);
                expect(this.doSomething).not.toBe(undefined);
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(false);
        await click("span");
        expect(clicked).toBe(true);
    });
});

describe("lifecycle", () => {
    test("lifecycle methods are called in order", async () => {
        let interaction = null;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                interaction = this;
                expect.step("setup");
            }
            willStart() {
                expect.step("willStart");
            }
            start() {
                expect.step("start");
            }
            destroy() {
                expect.step("destroy");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect.verifySteps(["setup", "willStart", "start"]);
        core.stopInteractions();
        expect.verifySteps(["destroy"]);
        expect(() => interaction.updateContent()).toThrow(
            "Cannot update the content of a destroyed interaction",
        );
    });

    test("willstart delayed, then destroy => start should not be called", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                expect.step("setup");
            }
            async willStart() {
                expect.step("willStart");
                return def;
            }
            start() {
                expect.step("start");
            }
            destroy() {
                expect.step("destroy");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest, {
            waitForStart: false,
        });
        expect.verifySteps(["setup", "willStart"]);
        core.stopInteractions();
        expect.verifySteps(["destroy"]);
        def.resolve();
        await animationFrame();
        expect.verifySteps([]);
    });

    test("willstart delayed => update => willstart complete", async () => {
        const def = new Deferred();
        let interaction;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                interaction = this;
            }
            async willStart() {
                expect.step("willStart");
                return def;
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(Test, TemplateTest, { waitForStart: false });
        expect.verifySteps(["willStart"]);
        expect(() => interaction.updateContent()).toThrow(
            "Cannot update the content of an interaction that has not started yet",
        );

        await animationFrame();
        expect.verifySteps([]);
        def.resolve();
        await animationFrame();
        expect.verifySteps(["start"]);
    });
});

describe("register cleanup", () => {
    test("can register a cleanup", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => {
                    expect.step("cleanup");
                });
            }
            destroy() {
                expect.step("destroy");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps(["cleanup", "destroy"]);
    });

    test("registerCleanup automatically bind functions", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.value = "value";
                this.registerCleanup(this.sayValue);
            }
            destroy() {
                expect.step("destroy");
            }
            sayValue() {
                return expect.step(this.value);
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps(["value", "destroy"]);
    });

    test("cleanups are executed in reverse order", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => {
                    expect.step("cleanup1");
                });
                this.registerCleanup(() => {
                    expect.step("cleanup2");
                });
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps(["cleanup2", "cleanup1"]);
    });

    test("cleanups registered before a throwing setup() still run", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => expect.step("cleanup"));
                throw new Error("boom");
            }
            destroy() {
                expect.step("destroy hook");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom");
        expect.verifySteps(["cleanup"]);
        expect(core.interactions).toHaveLength(0);
        await animationFrame();
        expect.verifyErrors([/boom/]);
    });

    test("a throwing cleanup does not skip the remaining teardown", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => expect.step("click") },
            };
            start() {
                this.registerCleanup(() => {
                    throw new Error("boom");
                });
            }
            destroy() {
                expect.step("destroy hook");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        await click(".test");
        expect.verifySteps(["click"]);

        expect(() => core.stopInteractions()).toThrow(
            "Could not destroy some interactions",
        );
        expect.verifySteps(["destroy hook"]);
        await click(".test");
        expect.verifySteps([]);
    });
});

describe("waitFor...", () => {
    describe("waitFor", () => {
        test("waitFor does not trigger update if interaction is not ready yet", async () => {
            class Test extends Interaction {
                static selector = ".test";
                async willStart() {
                    await this.waitFor(Promise.resolve(expect.step("waitfor")));
                    expect.step("willstart");
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            expect.step("timeout");
                            resolve();
                        }, 100);
                    });
                }
                start() {
                    expect.step("start");
                }
            }
            await startInteraction(Test, TemplateTest, { waitForStart: false });
            expect.verifySteps(["waitfor", "willstart"]);
            await advanceTime(150);
            expect.verifySteps(["timeout", "start"]);
        });

        test("waitFor triggers updateContent at the end of the callback queue", async () => {
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    _root: { "t-on-click": this.onClick },
                };
                async onClick() {
                    await this.waitFor(Promise.resolve(expect.step("waitfor")));
                    expect.step("clicked");
                }
                updateContent() {
                    expect.step("updatecontent");
                    super.updateContent();
                }
            }
            await startInteraction(Test, TemplateTest);
            expect.verifySteps([]);
            await click(".test");
            expect.verifySteps(["waitfor", "clicked", "updatecontent"]);
        });

        test("waitFor rethrow errors", async () => {
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    _root: { "t-on-click": this.onClick },
                };
                async onClick() {
                    try {
                        expect.step("before");
                        await this.waitFor(Promise.reject(new Error("boom")));
                        expect.step("after");
                    } catch (e) {
                        expect.step("in catch");
                        expect(e.message).toBe("boom");
                    }
                }
                updateContent() {
                    expect.step("updatecontent");
                    super.updateContent();
                }
            }
            await startInteraction(Test, TemplateTest);
            expect.verifySteps([]);
            await click(".test");
            expect.verifySteps(["before", "in catch", "updatecontent"]);
        });

        test("waitFor does not settle after a destroy, either way", async () => {
            const resolving = new Deferred();
            const rejecting = new Deferred();
            class Test extends Interaction {
                static selector = ".test";
                start() {
                    this.run(resolving, "resolving");
                    this.run(rejecting, "rejecting");
                }
                async run(deferred, label) {
                    try {
                        await this.waitFor(deferred);
                        expect.step(`${label}:then`);
                    } catch {
                        expect.step(`${label}:catch`);
                    }
                }
            }
            const { core } = await startInteraction(Test, TemplateTest);
            patchWithCleanup(core, {
                reportError(error) {
                    if (!(error instanceof Error)) {
                        throw error;
                    }
                    expect.step(`reported:${error.message}`);
                },
            });
            core.stopInteractions();
            resolving.resolve("nope");
            rejecting.reject(new Error("boom"));
            await animationFrame();
            expect.verifySteps(["reported:boom"]);
        });

        test("waitFor support promise is 'undefined'", async () => {
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    _root: { "t-on-click": this.onClick },
                };

                async onClick() {
                    await this.waitFor(undefined);
                    expect.step("clicked");
                }

                updateContent() {
                    expect.step("updatecontent");
                    super.updateContent();
                }
            }
            await startInteraction(Test, TemplateTest);
            expect.verifySteps([]);
            await click(".test");
            expect.verifySteps(["clicked", "updatecontent"]);
        });
    });

    describe("waitForTimeout", () => {
        test("waitForTimeout does not trigger update if interaction is not ready yet", async () => {
            class Test extends Interaction {
                static selector = ".test";
                async willStart() {
                    await this.waitForTimeout(() => expect.step("waitfortimeout"), 50);
                    expect.step("willstart");
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            expect.step("timeout");
                            resolve();
                        }, 100);
                    });
                }
                start() {
                    expect.step("start");
                }
            }
            await startInteraction(Test, TemplateTest, { waitForStart: false });
            expect.verifySteps(["willstart"]);
            await advanceTime(75);
            expect.verifySteps(["waitfortimeout"]);
            await advanceTime(75);
            expect.verifySteps(["timeout", "start"]);
        });

        test("waitForTimeout is autobound to this", async () => {
            class Test extends Interaction {
                static selector = ".test";
                setup() {
                    this.waitForTimeout(this.fn, 100);
                    this.waitForTimeout(() => {
                        expect(this instanceof Interaction).toBe(true);
                        expect.step("anonymous function");
                    }, 50);
                }
                fn() {
                    expect(this instanceof Interaction).toBe(true);
                    expect.step("named function");
                }
            }
            await startInteraction(Test, TemplateTest, { waitForStart: false });
            expect.verifySteps([]);
            await advanceTime(50);
            expect.verifySteps(["anonymous function"]);
            await advanceTime(50);
            expect.verifySteps(["named function"]);
        });

        test("waitForTimeout runs through protect", async () => {
            installProtect();
            class Test extends Interaction {
                static selector = ".test";
                setup() {
                    this.waitForTimeout(() => {
                        expect.step("done");
                    }, 100);
                }
            }
            await startInteraction(Test, TemplateTest);
            expect.verifySteps(["updateContent"]);
            await advanceTime(100);
            expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
        });
    });

    describe("waitForAnimationFrame", () => {
        test("waitForAnimationFrame does not trigger update if interaction is not ready yet", async () => {
            class Test extends Interaction {
                static selector = ".test";

                async willStart() {
                    await this.waitForAnimationFrame(() =>
                        expect.step("waitForAnimationFrame"),
                    );
                    expect.step("willstart");
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            expect.step("timeout");
                            resolve();
                        }, 100);
                    });
                }
                start() {
                    expect.step("start");
                }
            }
            await startInteraction(Test, TemplateTest, { waitForStart: false });
            expect.verifySteps(["willstart"]);
            await animationFrame();
            expect.verifySteps(["waitForAnimationFrame"]);
            await advanceTime(100);
            expect.verifySteps(["timeout", "start"]);
        });

        test("waitForAnimationFrame is autobound to this", async () => {
            class Test extends Interaction {
                static selector = ".test";
                setup() {
                    this.waitForAnimationFrame(this.fn);
                    this.waitForAnimationFrame(() => {
                        expect(this instanceof Interaction).toBe(true);
                        expect.step("anonymous function");
                    });
                }
                fn() {
                    expect(this instanceof Interaction).toBe(true);
                    expect.step("named function");
                }
            }
            await startInteraction(Test, TemplateTest, { waitForStart: false });
            expect.verifySteps([]);
            await animationFrame();
            expect.verifySteps(["named function", "anonymous function"]);
        });
    });

    test("waitForAnimationFrame runs through protect", async () => {
        installProtect();
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.waitForAnimationFrame(() => {
                    expect.step("done");
                });
            }
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["updateContent"]);
        await animationFrame();
        expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
    });

    test("pending timeout and animation frame are cancelled on destroy", async () => {
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.waitForTimeout(() => expect.step("timeout"), 1000);
                this.waitForAnimationFrame(() => expect.step("frame"));
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(core.interactions[0].cleanups).toHaveLength(2);
        core.stopInteractions();
        await advanceTime(1000);
        await animationFrame();
        expect.verifySteps([]);
    });

    test("a fired timeout does not accumulate in the cleanup list", async () => {
        /** @type {Test} */
        let interaction;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                interaction = this;
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        const colibri = core.interactions[0];
        for (let i = 0; i < 5; i++) {
            interaction.waitForTimeout(() => {}, 10);
        }
        expect(colibri.cleanups).toHaveLength(5);
        await advanceTime(10);
        expect(colibri.cleanups).toHaveLength(0);
    });
});

describe("t-att-class", () => {
    test("t-att-class can add a class ", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ a: true }) },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a");
    });

    test("t-att-class can add multiple classes ", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ "a b": true }) },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a b");
    });

    test("t-att-class can remove a class", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ a: false }) },
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("class='a'"));
        expect("span").not.toHaveClass("a");
    });

    test("t-att-class reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ a: true }) },
            };
        }
        const { core } = await startInteraction(Test, TemplateBase);
        core.stopInteractions();
        expect("span").not.toHaveClass("a");
    });

    test("t-att-class does not override existing classes", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ b: true }) },
            };
        }
        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("class='a'"),
        );
        expect("span").toHaveClass("a b");
        core.stopInteractions();
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
    });

    test("t-att-class accept variable", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-on-click": this.toggle,
                    "t-att-class": () => ({ a: this.var }),
                },
            };
            setup() {
                this.var = true;
            }
            toggle() {
                this.var = !this.var;
            }
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a");
        await click("span");
        await animationFrame();
        expect("span").not.toHaveClass("a");
        await click("span");
        await animationFrame();
        expect("span").toHaveClass("a");
    });

    test("t-att-class does not toggle on undefined", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ b: undefined }) },
            };
        }
        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("class='a b'"),
        );
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
        getInteraction(core, Test).updateContent();
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
    });

    test("t-att-class can manipulate multiple classes", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-on-click": this.toggle,
                    "t-att-class": () => ({ a: this.var, b: true, c: !this.var }),
                },
            };
            setup() {
                this.var = true;
            }
            toggle() {
                this.var = !this.var;
            }
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a b");
        expect("span").not.toHaveClass("c");
        await click("span");
        await animationFrame();
        expect("span").not.toHaveClass("a");
        expect("span").toHaveClass("b c");
    });

    test("t-att-class does not touch unrelated classes on destroy", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ b: true }) },
            };
        }

        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("class='a'"),
        );
        const span = queryOne("span");
        expect(span).toHaveClass(["a", "b"]);
        span.classList.add("c");
        expect(span).toHaveClass(["a", "b", "c"]);
        core.stopInteractions();
        expect(span).toHaveClass(["a", "c"]);
        expect(span).not.toHaveClass("b");
    });

    test("multi-class key restores each class to its own initial presence", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-class": () => ({ "e f": true }) },
            };
        }

        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("class='f'"),
        );
        expect("span").toHaveClass(["e", "f"]);
        core.stopInteractions();
        expect("span").not.toHaveClass("e");
        expect("span").toHaveClass("f");
    });

    test("reset t-att-class to initial content", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-att-class": () => ({
                        a: true,
                        b: false,
                        c: this.withClass,
                        d: this.withClass,
                        "e f": this.withClass,
                    }),
                },
            };
            setup() {
                this.withClass = true;
            }
            start() {
                this.waitForTimeout(() => {
                    this.withClass = Interaction.INITIAL_VALUE;
                }, 1000);
            }
        }
        await startInteraction(
            Test,
            `<div class="test"><span class="b d">Hi</span></div>`,
        );
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
        expect("span").toHaveClass("c");
        expect("span").toHaveClass("d");
        expect("span").toHaveClass("e");
        expect("span").toHaveClass("f");
        await advanceTime(1000);
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
        expect("span").not.toHaveClass("c");
        expect("span").toHaveClass("d");
        expect("span").not.toHaveClass("e");
        expect("span").not.toHaveClass("f");
    });
});

describe("t-att-style", () => {
    test("t-att-style can add a style", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: "red" }) },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style can remove a style", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: undefined }) },
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("style='color: red;'"));
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: "red" }) },
            };
        }
        const { core } = await startInteraction(Test, TemplateBase);
        core.stopInteractions();
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style only resets changed style", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-att-style": () => ({
                        "background-color": "black",
                        color: "red",
                    }),
                },
            };
        }

        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("style='background-color: blue'"),
        );
        const span = queryOne("span");
        expect(span).toHaveStyle({
            "background-color": "rgb(0, 0, 0)",
            color: "rgb(255, 0, 0)",
        });
        span.style.setProperty("width", "50%");
        expect(span).toHaveStyle({
            "background-color": "rgb(0, 0, 0)",
            color: "rgb(255, 0, 0)",
            width: "50%",
        });
        core.stopInteractions();
        expect(span).toHaveStyle({
            "background-color": "rgb(0, 0, 255)",
            width: "50%",
        });
        expect(span).not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style restores priority on reset", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-att-style": () => ({
                        "background-color": "black",
                        color: "red",
                    }),
                },
            };
        }

        const { core } = await startInteraction(
            Test,
            `<div><span style="background-color: blue !important">coucou</span></div>`,
        );
        const span = queryOne("span");
        expect(span).toHaveOuterHTML(
            `<span style="background-color: black; color: red;">coucou</span>`,
        );
        span.style.setProperty("width", "50%", "important");
        expect(span).toHaveOuterHTML(
            `<span style="background-color: black; color: red; width: 50% !important;">coucou</span>`,
        );
        core.stopInteractions();
        expect(span).toHaveOuterHTML(
            `<span style="background-color: blue !important; width: 50% !important;">coucou</span>`,
        );
    });

    test("t-att-style does not override existing styles", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: "red" }) },
            };
        }
        const { core } = await startInteraction(
            Test,
            getTemplateWithAttribute("style='background-color: blue;'"),
        );
        expect("span").toHaveStyle({
            backgroundColor: "rgb(0, 0, 255)",
            color: "rgb(255, 0, 0)",
        });
        core.stopInteractions();
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style accept variable", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-on-click": this.toggle,
                    "t-att-style": () => ({ color: this.var }),
                },
            };
            setup() {
                this.var = "red";
            }
            toggle() {
                this.var = this.var === "red" ? "blue" : "red";
            }
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
        await click("span");
        await animationFrame();
        expect("span").toHaveStyle({ color: "rgb(0, 0, 255)" });
        await click("span");
        await animationFrame();
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style accept non-string", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ opacity: 1 }) },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ opacity: "1" });
    });

    test("t-att-style can manipulate multiple styles", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-on-click": this.toggle,
                    "t-att-style": () => ({
                        "background-color": this.b,
                        color: this.c,
                    }),
                },
            };
            setup() {
                this.b = "blue";
                this.c = "red";
            }
            toggle() {
                this.b = this.b === "red" ? "blue" : "red";
                this.c = this.c === "red" ? "blue" : "red";
            }
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({
            color: "rgb(255, 0, 0)",
            backgroundColor: "rgb(0, 0, 255)",
        });
        await click("span");
        await animationFrame();
        expect("span").toHaveStyle({
            color: "rgb(0, 0, 255)",
            backgroundColor: "rgb(255, 0, 0)",
        });
    });

    test("t-att-style, apply important", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: "red !important" }) },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveOuterHTML(
            `<span style="color: red !important;">coucou</span>`,
        );
    });

    test("reset t-att-style to initial content", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-att-style": () => ({
                        "background-color": this.bgColor,
                        color: this.color,
                    }),
                },
            };
            setup() {
                this.bgColor = "rgb(0, 255, 0)";
                this.color = "rgb(255, 0, 0)";
            }
            start() {
                this.waitForTimeout(() => {
                    this.bgColor = Interaction.INITIAL_VALUE;
                    this.color = Interaction.INITIAL_VALUE;
                }, 1000);
            }
        }
        await startInteraction(
            Test,
            `<div class="test" style="color: black;"><span style="background-color: rgb(0, 0, 255);">Hi</span></div>`,
        );
        expect("span").toHaveStyle({
            "background-color": "rgb(0, 255, 0)",
            color: "rgb(255, 0, 0)",
        });
        await advanceTime(1000);
        expect("span").toHaveStyle({
            "background-color": "rgb(0, 0, 255)",
            color: "rgb(0, 0, 0)",
        });
    });
});

describe("t-att and t-out", () => {
    test("t-att-... can add an attribute", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-a": () => "b" },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveAttribute("a", "b");
    });

    test("t-att-... can remove an attribute", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-a": () => undefined },
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("a='b'"));
        expect("span").not.toHaveAttribute("a");
    });

    test("t-att-... with boolean true adds a boolean attribute", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-disabled": () => true },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveAttribute("disabled", "disabled");
    });

    test("t-att-... with empty string adds an empty string", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-disabled": () => "" },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveAttribute("disabled", "");
    });

    test("t-att-... with number 0 adds a '0' string", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-a": () => 0 },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveAttribute("a", "0");
    });

    test("t-att-... reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-a": () => "b" },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        core.stopInteractions();
        expect("span").not.toHaveAttribute("a");
    });

    test("t-att-... save previously loaded attributes", async () => {
        const c = [{ a: true }, { b: true }];
        const s = [{ "background-color": "blue" }, { color: "red" }];
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-att-class": () => c.pop(),
                    "t-att-style": () => s.pop(),
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateBase);
        expect("span").not.toHaveClass("a");
        expect("span").toHaveClass("b");
        expect("span").not.toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
        getInteraction(core, Test).updateContent();
        await animationFrame();
        expect("span").toHaveClass("a");
        expect("span").toHaveClass("b");
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-... receive the target as argument", async () => {
        /** @type {HTMLElement} */
        let target;
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: {
                    "t-att-a": (_el) => {
                        target = _el;
                        return "b";
                    },
                },
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveAttribute("a", "b");
        expect(target).toBe(queryOne("span"));
    });

    test("t-att-... restores all values on stop", async () => {
        class Test extends Interaction {
            static selector = "div";
            dynamicContent = {
                span: { "t-att-data-animal": () => undefined },
            };
        }
        const { core } = await startInteraction(
            Test,
            `
            <div>
                <span data-animal="colibri">1</span>
                <span data-animal="owlet">2</span>
            </div>
        `,
        );
        expect("span:first").not.toHaveAttribute("data-animal");
        expect("span:last").not.toHaveAttribute("data-animal");
        core.stopInteractions();
        expect("span:first").toHaveAttribute("data-animal", "colibri");
        expect("span:last").toHaveAttribute("data-animal", "owlet");
    });

    test("t-att-... restores all values on stop even if swapped", async () => {
        class Test extends Interaction {
            static selector = "div";
            dynamicContent = {
                span: { "t-att-data-animal": () => undefined },
            };
        }
        const { core } = await startInteraction(
            Test,
            `
            <div>
                <span data-animal="colibri">1</span>
                <span data-animal="owlet">2</span>
            </div>
        `,
        );
        expect("span:first").not.toHaveAttribute("data-animal");
        expect("span:last").not.toHaveAttribute("data-animal");
        const firstSpan = queryOne("span:first");
        firstSpan.parentElement.appendChild(firstSpan);
        core.stopInteractions();
        expect("span:last").toHaveAttribute("data-animal", "colibri");
        expect("span:first").toHaveAttribute("data-animal", "owlet");
    });

    test("can do a simple t-out", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-out": () => "colibri" },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveText("colibri");
    });

    test("markup'd t-out restarts the internal interactions", async () => {
        let oldInnerInteraction, newInnerInteraction;
        before(() => {
            clearRegistry(registry);
            class OldInner extends Interaction {
                static selector = ".old-inner";
                dynamicContent = {
                    _root: { "t-att-animal": () => "unicorn" },
                };
            }
            oldInnerInteraction = OldInner;
            class Inner extends Interaction {
                static selector = ".inner";
                dynamicContent = {
                    _root: { "t-att-animal": () => "colibri" },
                };
            }
            newInnerInteraction = Inner;
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    _root: {
                        "t-out": () => {
                            expect.step("t-out");
                            return this.tOut;
                        },
                    },
                    span: {
                        "t-on-click.noUpdate": () => {
                            expect.step("clicked");
                        },
                    },
                };
                setup() {
                    this.tOut = markup`<span class="old-inner">Hi</span>`;
                }
                start() {
                    this.waitForTimeout(() => {
                        this.tOut = markup`<span class='inner'>Hello</span>`;
                    }, 1000);
                }
            }
            for (const I of [OldInner, Inner, Test]) {
                registry.category("public.interactions").add(I.name, I);
            }
        });
        const { core } = await startInteractions(`<div class="test"></div>`);
        expect.verifySteps(["t-out"]);
        const oldInner = queryOne(".old-inner");
        expect("span").toHaveClass("old-inner");
        expect("span").toHaveAttribute("animal", "unicorn");
        expect(core.activeInteractions.map.get(oldInner).has(oldInnerInteraction)).toBe(
            true,
        );
        await advanceTime(1000);
        expect.verifySteps(["t-out"]);
        const inner = queryOne(".inner");
        expect("span").not.toHaveClass("old-inner");
        expect("span").toHaveAttribute("animal", "colibri");
        expect("span").toHaveClass("inner");
        expect(core.activeInteractions.map.get(oldInner)).toBe(undefined);
        expect(core.activeInteractions.map.get(inner).has(newInnerInteraction)).toBe(
            true,
        );
        await click("span");
        expect.verifySteps(["clicked"]);
    });

    test("reset t-out to initial content", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-out": () => this.tOut },
            };
            setup() {
                this.tOut = "colibri";
            }
            start() {
                this.waitForTimeout(() => {
                    /** @type {string | symbol | import("@odoo/owl").Markup} */
                    this.tOut = Interaction.INITIAL_VALUE;
                }, 1000);
            }
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveText("colibri");
        await advanceTime(1000);
        expect("span").toHaveText("coucou");
    });

    test("reset t-att to initial content", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-att-animal": () => this.animal,
                    "t-att-egg": () => this.egg,
                },
            };
            setup() {
                this.animal = "colibri";
                this.egg = "easter";
            }
            start() {
                this.waitForTimeout(() => {
                    this.animal = Interaction.INITIAL_VALUE;
                    this.egg = Interaction.INITIAL_VALUE;
                }, 1000);
            }
        }
        await startInteraction(
            Test,
            `<div class="test"><span egg="mysterious"></span></div>`,
        );
        expect("span").toHaveAttribute("animal", "colibri");
        expect("span").toHaveAttribute("egg", "easter");
        await advanceTime(1000);
        expect("span").not.toHaveAttribute("animal");
        expect("span").toHaveAttribute("egg", "mysterious");
    });

    test("t-out-... resets at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-out": () => "colibri" },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect("span").toHaveText("colibri");
        core.stopInteractions();
        expect("span").toHaveText("coucou");
    });

    test("t-out-... restores all values on stop", async () => {
        class Test extends Interaction {
            static selector = "div";
            dynamicContent = {
                span: { "t-out": () => "colibri" },
            };
        }
        const { core } = await startInteraction(
            Test,
            `
            <div>
                <span>penguin</span>
                <span>ostrich</span>
            </div>
        `,
        );
        expect("span").toHaveText("colibri");
        core.stopInteractions();
        expect("span:first").toHaveText("penguin");
        expect("span:last").toHaveText("ostrich");
    });

    test("plain-string t-out stops child interactions before wiping them", async () => {
        let innerInteraction;
        before(() => {
            clearRegistry(registry);
            class Inner extends Interaction {
                static selector = ".inner";
                dynamicContent = {
                    _root: { "t-att-animal": () => "colibri" },
                };
            }
            innerInteraction = Inner;
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    _root: { "t-out": () => this.tOut },
                };
                setup() {
                    this.tOut = Interaction.INITIAL_VALUE;
                }
                start() {
                    this.waitForTimeout(() => {
                        this.tOut = "goodbye";
                    }, 1000);
                }
            }
            for (const I of [Inner, Test]) {
                registry.category("public.interactions").add(I.name, I);
            }
        });
        const { core } = await startInteractions(
            `<div class="test"><span class="inner">Hi</span></div>`,
        );
        const inner = queryOne(".inner");
        expect(".inner").toHaveAttribute("animal", "colibri");
        expect(core.activeInteractions.map.get(inner).has(innerInteraction)).toBe(true);
        await advanceTime(1000);
        expect(".test").toHaveText("goodbye");
        expect(".inner").toHaveCount(0);
        expect(core.activeInteractions.map.get(inner)).toBe(undefined);
    });

    test("t-out stops every child, even one whose cleanup detaches itself", async () => {
        class SelfRemoving extends Interaction {
            static selector = ".child";
            setup() {
                this.registerCleanup(() => {
                    expect.step(`stopped:${this.el.dataset.n}`);
                    this.el.remove();
                });
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { _root: { "t-out": () => this.tOut } };
            setup() {
                this.tOut = "wiped";
            }
        }
        const kids = [1, 2, 3, 4]
            .map((n) => `<span class="child" data-n="${n}"></span>`)
            .join("");
        const { core } = await startInteraction(
            [SelfRemoving, Test],
            `<div class="test">${kids}</div>`,
        );
        expect.verifySteps(["stopped:1", "stopped:2", "stopped:3", "stopped:4"]);
        expect(core.interactions).toHaveLength(1);
        expect(".test").toHaveText("wiped");
    });

    test("a markup t-out that yields the same markup leaves the subtree alone", async () => {
        let starts = 0;
        let destroys = 0;
        class Inner extends Interaction {
            static selector = ".inner";
            setup() {
                starts++;
            }
            destroy() {
                destroys++;
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => markup`<span class="inner">Hi</span>` },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Inner, Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        expect(starts).toBe(1);
        const inner = queryOne(".inner");
        await click(".btn");
        expect([starts, destroys]).toEqual([1, 0]);
        expect(queryOne(".inner")).toBe(inner);
    });

    test("a t-att reaches the nodes a t-out built in the same pass", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.n = 0;
            }
            dynamicContent = {
                ".slot": {
                    "t-out": () => markup(`<span class="b">${this.n}</span>`),
                },
                ".b": { "t-att-data-n": () => String(this.n) },
                ".btn": { "t-on-click": () => this.n++ },
            };
        }
        await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        expect(queryOne(".b")).toHaveAttribute("data-n", "0");
        await click(".btn");
        expect(queryOne(".b")).toHaveText("1");
        expect(queryOne(".b")).toHaveAttribute("data-n", "1");
    });

    test("a markup t-out that already agrees with the server markup is a no-op", async () => {
        const HTML = `<span class="inner">Hi</span>`;
        let starts = 0;
        class Inner extends Interaction {
            static selector = ".inner";
            setup() {
                starts++;
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => markup(HTML) },
            };
        }
        await startInteraction(
            [Inner, Test],
            `<div class="test"><div class="slot">${HTML}</div></div>`,
        );
        const inner = queryOne(".inner");
        await animationFrame();
        expect(starts).toBe(1);
        expect(queryOne(".inner")).toBe(inner);
    });

    test("a markup t-out still rebuilds server markup another hand has changed", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => markup(`<span class="inner">Hi</span>`) },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"><span class="inner">tampered</span></div></div>`,
        );
        await animationFrame();
        expect(".inner").toHaveText("Hi");
    });

    test("a plain t-out that yields the same text keeps the text node", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => "stable" },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        const textNode = queryOne(".slot").firstChild;
        expect(".slot").toHaveText("stable");
        await click(".btn");
        expect(queryOne(".slot").firstChild).toBe(textNode);
    });

    test("a t-out still rewrites content another hand has changed", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => "stable" },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        queryOne(".slot").textContent = "tampered";
        await click(".btn");
        expect(".slot").toHaveText("stable");
    });

    test("a markup t-out still rewrites a subtree another hand has changed", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => markup(`<span class="in">stable</span>`) },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        expect(".slot").toHaveInnerHTML(`<span class="in">stable</span>`);
        queryOne(".slot").innerHTML = `<span class="in">tampered</span>`;
        await click(".btn");
        expect(".slot").toHaveInnerHTML(`<span class="in">stable</span>`);
    });

    test("a markup t-out does not restart the interactions it decorates", async () => {
        let innerStarts = 0;
        class Inner extends Interaction {
            static selector = ".inner";
            dynamicContent = { _root: { "t-att-data-live": () => "yes" } };
            setup() {
                innerStarts++;
            }
        }
        class Outer extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => markup(`<div class="inner"></div>`) },
            };
        }
        const { core } = await startInteraction(
            [Outer, Inner],
            `<div class="test"><div class="slot"></div></div>`,
        );
        await animationFrame();
        const innerEl = queryOne(".inner");
        for (let i = 0; i < 3; i++) {
            getInteraction(core, Outer).updateContent();
            await animationFrame();
        }
        expect(innerStarts).toBe(1);
        expect(queryOne(".inner")).toBe(innerEl);
    });

    test("agreeing server markup is adopted, decorations and all", async () => {
        const HTML = `<div class="inner">Hi</div>`;
        let innerStarts = 0;
        class Inner extends Interaction {
            static selector = ".inner";
            dynamicContent = { _root: { "t-att-data-live": () => "yes" } };
            setup() {
                innerStarts++;
            }
        }
        class Outer extends Interaction {
            static selector = ".test";
            dynamicContent = { ".slot": { "t-out": () => markup(HTML) } };
        }
        const { core } = await startInteraction(
            [Outer, Inner],
            `<div class="test"><div class="slot">${HTML}</div></div>`,
        );
        await animationFrame();
        const innerEl = queryOne(".inner");
        for (let i = 0; i < 3; i++) {
            getInteraction(core, Outer).updateContent();
            await animationFrame();
        }
        expect(innerStarts).toBe(1);
        expect(queryOne(".inner")).toBe(innerEl);
    });

    test("a churning selector does not keep a reference per node it ever saw", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-out": () => this.tOut },
                ".row": { "t-att-data-n": () => "x" },
            };
            setup() {
                this.tOut = markup(`<div class="row">0</div>`);
            }
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        const interaction = getInteraction(core, Test);
        for (let i = 1; i <= 300; i++) {
            interaction.tOut = markup(`<div class="row">${i}</div>`);
            interaction.updateContent();
        }
        const { touched } = core.interactions[0].dynamicAttrs[0];
        expect(touched.size).toBeGreaterThan(1);
        if (typeof globalThis.gc !== "function") {
            return;
        }
        for (let i = 0; i < 2; i++) {
            await new Promise((resolve) => setTimeout(resolve, 0));
            globalThis.gc();
        }
        await new Promise((resolve) => setTimeout(resolve, 0));
        let live = 0;
        for (const ref of touched) {
            if (ref.deref()) {
                live++;
            }
        }
        expect(live).toBe(1);
        expect(touched.size).toBeLessThan(50);
    });

    test("a t-out alternating between markup and text applies both", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                /** @type {string | import("@odoo/owl").Markup} */
                this.tOut = markup`<i>a</i>`;
            }
            dynamicContent = {
                ".slot": { "t-out": () => this.tOut },
            };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        const interaction = getInteraction(core, Test);
        expect(".slot").toHaveInnerHTML(`<i>a</i>`);
        interaction.tOut = "<i>a</i>";
        interaction.updateContent();
        expect(".slot").toHaveText("<i>a</i>");
        expect(".slot i").toHaveCount(0);
        interaction.tOut = markup`<i>a</i>`;
        interaction.updateContent();
        expect(".slot i").toHaveCount(1);
    });

    test("a t-out spares the interaction rooted on its own node", async () => {
        let starts = 0;
        let destroys = 0;
        class Slot extends Interaction {
            static selector = ".slot";
            setup() {
                starts++;
            }
            destroy() {
                destroys++;
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                /** @type {string | import("@odoo/owl").Markup} */
                this.tOut = "a";
            }
            dynamicContent = {
                ".slot": { "t-out": () => this.tOut },
            };
        }
        const { core } = await startInteraction(
            [Slot, Test],
            `<div class="test"><div class="slot"><i>x</i></div></div>`,
        );
        expect(starts).toBe(1);
        const interaction = getInteraction(core, Test);
        interaction.tOut = "b";
        interaction.updateContent();
        expect(".slot").toHaveText("b");
        expect([starts, destroys]).toEqual([1, 0]);
        interaction.tOut = markup`<i>c</i>`;
        interaction.updateContent();
        expect(".slot").toHaveInnerHTML(`<i>c</i>`);
        expect([starts, destroys]).toEqual([1, 0]);
    });

    test("a t-att that yields the same value does not touch the dom", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": {
                    "t-att-data-x": () => "stable",
                    "t-att-style": () => ({ color: "red" }),
                    "t-att-class": () => ({ on: true }),
                },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        expect(".slot").toHaveAttribute("data-x", "stable");
        const records = [];
        const observer = new MutationObserver((rs) => records.push(...rs));
        observer.observe(queryOne(".test"), { attributes: true, subtree: true });
        await click(".btn");
        observer.disconnect();
        expect(records).toHaveLength(0);
    });

    test("a t-att still rewrites an attribute another hand has changed", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".slot": { "t-att-data-x": () => "stable" },
                ".btn": { "t-on-click": () => {} },
            };
        }
        await startInteraction(
            [Test],
            `<div class="test"><div class="slot"></div><button class="btn">b</button></div>`,
        );
        queryOne(".slot").setAttribute("data-x", "tampered");
        await click(".btn");
        expect(".slot").toHaveAttribute("data-x", "stable");
    });

    test("t-out: the focus, selection and scroll of a subtree survive an unchanged update", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.tOut = markup`<input class="typed"/><div class="scroller" style="height:20px;overflow:auto"><div style="height:400px"></div></div>`;
            }
            dynamicContent = { ".slot": { "t-out": () => this.tOut } };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        const input = queryOne(".typed");
        const scroller = queryOne(".scroller");
        input.focus();
        scroller.scrollTop = 120;
        expect(document.activeElement).toBe(input);
        core.interactions[0].updateContent();
        expect(document.activeElement).toBe(input);
        expect(queryOne(".scroller").scrollTop).toBe(120);
        getInteraction(core, Test).tOut = markup`<input class="typed" data-v="2"/>`;
        core.interactions[0].updateContent();
        expect(queryOne(".typed")).not.toBe(input);
    });

    test("a plain t-out keeps a text selection the visitor is making", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { ".slot": { "t-out": () => "hello world" } };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        const textNode = /** @type {Text} */ (queryOne(".slot").firstChild);
        const range = document.createRange();
        range.setStart(textNode, 0);
        range.setEnd(textNode, 5);
        const selection = /** @type {Selection} */ (window.getSelection());
        selection.removeAllRanges();
        selection.addRange(range);
        expect(selection.toString()).toBe("hello");
        core.interactions[0].updateContent();
        expect(String(window.getSelection())).toBe("hello");
    });

    test("a plain t-out reproduces the textContent setter exactly", async () => {
        const probe = document.createElement("div");
        for (const nullish of [null, undefined]) {
            probe.textContent = /** @type {any} */ (nullish);
            expect(probe.textContent).toBe("");
        }

        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.tOut = null;
            }
            dynamicContent = { ".slot": { "t-out": () => this.tOut } };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot">x</div></div>`,
        );
        expect(queryOne(".slot").childNodes).toHaveLength(0);
        const interaction = getInteraction(core, Test);
        interaction.tOut = undefined;
        core.interactions[0].updateContent();
        expect(queryOne(".slot").childNodes).toHaveLength(0);
        queryOne(".slot").textContent = "undefined";
        core.interactions[0].updateContent();
        expect(queryOne(".slot").childNodes).toHaveLength(0);
        interaction.tOut = 0;
        core.interactions[0].updateContent();
        expect(".slot").toHaveText("0");
    });

    test("a plain t-out is not fooled by a comment or a split text node", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { ".slot": { "t-out": () => "ab" } };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        const slot = queryOne(".slot");
        slot.replaceChildren(
            document.createTextNode("a"),
            document.createTextNode("b"),
        );
        core.interactions[0].updateContent();
        expect(slot.childNodes).toHaveLength(1);
        slot.replaceChildren(
            document.createComment("c"),
            document.createTextNode("ab"),
        );
        core.interactions[0].updateContent();
        expect(slot.childNodes).toHaveLength(1);
        expect(".slot").toHaveText("ab");
    });

    test("two t-out entries on one node still let the last one win", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.a = markup`<i>A</i>`;
                this.b = markup`<i>B</i>`;
            }
            dynamicContent = {
                ".slot": { "t-out": () => this.a },
                "div.slot": { "t-out": () => this.b },
            };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot"></div></div>`,
        );
        expect(".slot").toHaveInnerHTML(`<i>B</i>`);
        getInteraction(core, Test).a = markup`<i>A2</i>`;
        core.interactions[0].updateContent();
        expect(".slot").toHaveInnerHTML(`<i>B</i>`);
    });

    test("a t-att value that changes is still written through the guard", async () => {
        class Test extends Interaction {
            static selector = ".test";
            hidden = false;
            setup() {
                /** @type {string | number} */
                this.v = "1";
            }
            dynamicContent = {
                ".slot": {
                    "t-att-data-x": () => this.v,
                    "t-att-hidden": () => this.hidden,
                },
            };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><div class="slot" data-y="keep"></div></div>`,
        );
        expect(".slot").toHaveAttribute("data-x", "1");
        expect(".slot").not.toHaveAttribute("hidden");
        const interaction = getInteraction(core, Test);
        interaction.v = 2;
        interaction.hidden = true;
        core.interactions[0].updateContent();
        expect(".slot").toHaveAttribute("data-x", "2");
        expect(".slot").toHaveAttribute("hidden", "hidden");
        interaction.hidden = false;
        core.interactions[0].updateContent();
        expect(".slot").not.toHaveAttribute("hidden");
    });

    test("a markup t-out rescans the subtree once, not once per child", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { _root: { "t-out": () => this.tOut } };
            setup() {
                /** @type {symbol | import("@odoo/owl").Markup} */
                this.tOut = Interaction.INITIAL_VALUE;
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        patchWithCleanup(core, {
            startInteractions(el) {
                expect.step("scan");
                return super.startInteractions(el);
            },
        });
        const interaction = getInteraction(core, Test);
        interaction.tOut = markup(`<i></i><i></i><i></i><i></i>`);
        interaction.updateContent();
        expect.verifySteps(["scan"]);
        expect(".test i").toHaveCount(4);
    });
});

describe("components", () => {
    test("can insert a component with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`component`;
            static props = {};

            setup() {
                onWillDestroy(() => {
                    isCDestroyed = true;
                });
            }
        }

        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-component": C },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">component</owl-root></div>`,
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
    });

    test("can insert a component with props with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`<p>component<span t-out="this.props.prop"></span></p>`;
            static props = {
                prop: { optional: true, type: String },
            };

            setup() {
                onWillDestroy(() => {
                    isCDestroyed = true;
                });
            }
        }

        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-component": () => [C, { prop: "hello" }] },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;"><p>component<span>hello</span></p></owl-root></div>`,
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
    });

    test("can receive the selected element with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`<p>component<span t-out="this.props.prop"></span></p>`;
            static props = {
                prop: { optional: true, type: String },
            };

            setup() {
                onWillDestroy(() => {
                    isCDestroyed = true;
                });
            }
        }

        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-component": (el) => [C, { prop: el.className }] },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;"><p>component<span>test</span></p></owl-root></div>`,
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
    });

    test("can insert a component at certain position", async () => {
        class C extends Component {
            static template = xml`component`;
            static props = {};
        }
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const el = document.createElement("span");
                this.insert(el, this.el);
                this.mountComponent(el, C, null, "beforebegin");
            }
        }
        await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">component</owl-root><span></span></div>`,
        );
    });

    test("can insert a component with mountComponent", async () => {
        class C extends Component {
            static template = xml`component`;
            static props = {};
        }

        /** @type {() => void} */
        let destroy;
        class Test extends Interaction {
            static selector = ".test";

            setup() {
                destroy = this.mountComponent(this.el, C);
            }
        }
        await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">component</owl-root></div>`,
        );
        destroy();
        expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
        destroy();
        expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
    });

    test("can insert a component with props with mountComponent", async () => {
        class C extends Component {
            static template = xml`<p>component<span t-out="this.props.prop"></span></p>`;
            static props = {
                prop: { optional: true, type: String },
            };
        }

        class Test extends Interaction {
            static selector = ".test";

            setup() {
                this.mountComponent(this.el, C, { prop: "with prop" });
            }
        }
        await startInteraction(Test, `<div class="test"></div>`);
        expect(".test").toHaveOuterHTML(
            `<div class="test"><owl-root contenteditable="false" data-oe-protected="true" style="display: contents;"><p>component<span>with prop</span></p></owl-root></div>`,
        );
    });
});

describe("insert", () => {
    test("can insert an element and update dynamicAttrs and dynamicNodes", async () => {
        const el1 = document.createElement("div");
        el1.classList.add("very-cool-class");
        const el2 = document.createElement("div");
        el2.classList.add("very-cool-class");
        /** @type {Test} */
        let interaction;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".very-cool-class": {
                    "t-att-style": () => ({ display: "block" }),
                },
            };
            setup() {
                interaction = this;
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        interaction.insert(el1, interaction.el);
        const dynNode1 = interaction.__colibri__.dynamicNodes.values().next().value[0];
        expect(dynNode1).toBe(el1);
        interaction.updateContent();
        const initialValues = interaction.__colibri__.dynamicAttrs[0].initialValues;
        expect(initialValues).toBeInstanceOf(WeakMap);
        expect(initialValues.has(el1)).toBe(true);
        el1.remove();
        interaction.insert(el2, interaction.el);
        const dynNode2 = interaction.__colibri__.dynamicNodes.values().next().value[0];
        expect(dynNode2).toBe(el2);
        expect(initialValues.has(el2)).toBe(false);
        interaction.updateContent();
        expect(initialValues.has(el2)).toBe(true);
        core.stopInteractions();
    });

    test("can insert an element after another nested", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const node = document.createElement("inserted");
                this.insert(node, this.el);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryOne(".test inserted:last-child")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst("inserted")).toBe(null);
    });

    test("can insert an element before another nested", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const node = document.createElement("inserted");
                this.insert(node, this.el, "afterbegin");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryOne(".test inserted:first-child")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst("inserted")).toBe(null);
    });

    test("can insert an element before another one", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const span = this.el.querySelector("span");
                const node = document.createElement("inserted");
                this.insert(node, span, "beforebegin");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryOne(".test inserted + span")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst("inserted")).toBe(null);
    });

    test("can insert an element after another one", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const span = this.el.querySelector("span");
                const node = document.createElement("inserted");
                this.insert(node, span, "afterend");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryOne(".test span + inserted")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst("inserted")).toBe(null);
    });

    test("inserted element is kept if removeOnClean is false", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const node = document.createElement("inserted");
                this.insert(node, this.el, "beforeend", false);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryOne(".test inserted:last-child")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst("inserted")).toBeInstanceOf(HTMLElement);
    });
});

describe("removeChildren", () => {
    test("can remove text child", async () => {
        class Test extends Interaction {
            static selector = ".test span";
            setup() {
                this.removeChildren(this.el);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(".test span").toHaveInnerHTML("");
        core.stopInteractions();
        expect(".test span").toHaveInnerHTML("coucou");
    });

    test("can remove element children", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.removeChildren(this.el);
            }
        }

        const { core } = await startInteraction(Test, TemplateTestDoubleSpan);
        expect(queryFirst(".test span")).toBe(null);
        core.stopInteractions();
        expect(queryFirst(".test span")).toBeInstanceOf(HTMLElement);
        expect(queryAll(".test span")).toHaveCount(2);
    });

    test("can remove element with removed children", async () => {
        let innerDoneResolve;
        const innerDonePromise = new Promise((resolve) => (innerDoneResolve = resolve));
        class InnerTest extends Interaction {
            static selector = ".test span";
            setup() {
                this.removeChildren(this.el);
                innerDoneResolve();
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            async willStart() {
                await innerDonePromise;
                this.removeChildren(this.el);
            }
        }

        const { core } = await startInteraction([InnerTest, Test], TemplateTest);
        expect(queryFirst(".test span")).toBe(null);
        core.stopInteractions();
        expect(queryOne(".test span")).toHaveInnerHTML("coucou");
    });

    test("removed children do not come back if insertBackOnClean is false", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.removeChildren(this.el, false);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryFirst(".test span")).toBe(null);
        core.stopInteractions();
        expect(queryFirst(".test span")).toBe(null);
    });

    test("re-insert initial children", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.removeChildren(this.el);
                this.el.innerHTML = TemplateTestDoubleButton;
                this.removeChildren(this.el);
            }
        }

        const { core } = await startInteraction(Test, TemplateTest);
        expect(queryFirst(".test span")).toBe(null);
        core.stopInteractions();
        expect(queryOne(".test span")).toBeInstanceOf(HTMLElement);
        expect(queryFirst(".test button")).toBe(null);
    });

    test("stops every child, even one whose cleanup detaches itself", async () => {
        class SelfRemoving extends Interaction {
            static selector = ".child";
            setup() {
                this.registerCleanup(() => {
                    expect.step(`stopped:${this.el.dataset.n}`);
                    this.el.remove();
                });
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.removeChildren(this.el);
            }
        }
        const kids = [1, 2, 3, 4]
            .map((n) => `<span class="child" data-n="${n}"></span>`)
            .join("");
        const { core } = await startInteraction(
            [SelfRemoving, Test],
            `<div class="test">${kids}</div>`,
        );
        expect.verifySteps(["stopped:1", "stopped:2", "stopped:3", "stopped:4"]);
        expect(core.interactions).toHaveLength(1);
    });

    test("a child whose destroy throws does not strand the removal", async () => {
        expect.errors(1);
        class Boom extends Interaction {
            static selector = ".boom";
            destroy() {
                throw new Error("child destroy blew up");
            }
        }
        class Sibling extends Interaction {
            static selector = ".sibling";
            destroy() {
                expect.step("sibling stopped");
            }
        }
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.removeChildren(this.el);
                expect.step("caller survived");
            }
        }
        const { core } = await startInteraction(
            [Boom, Sibling, Test],
            `<div class="test"><div class="boom"></div><div class="sibling"></div></div>`,
        );
        expect.verifySteps(["sibling stopped", "caller survived"]);
        expect(".test").toHaveInnerHTML("");
        expect(core.interactions).toHaveLength(1);
        await animationFrame();
        expect.verifyErrors([/Could not destroy some interactions/]);

        core.stopInteractions();
        expect(".test .boom").toHaveCount(1);
        expect(".test .sibling").toHaveCount(1);
    });
});

describe("renderAt", () => {
    test("renders a context-free template without being handed a context", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.renderAt("web.public.test.norender");
            }
        }
        await startInteraction(Test, `<div class="test"></div>`);
        expect(".test .no-context").toHaveCount(1);
    });

    test("renders several elements with a single interaction scan", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.renderAt(
                    "web.TestSubInteraction1",
                    { first: "one", second: "two" },
                    this.el,
                );
            }
        }
        const { core } = await startInteractionsCounted([Test], TemplateTest);
        expect(core.scanCount).toBe(1);
        expect(queryAll(".test [data-which]")).toHaveLength(2);
    });

    test("can render a template inside an element", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "[data-which]": {
                    "t-on-click": (ev) => expect.step(ev.target.dataset.which),
                },
            };
            setup() {
                this.renderAt(
                    "web.TestSubInteraction1",
                    {
                        first: "one",
                        second: "two",
                    },
                    this.el,
                );
            }
        }
        class Test2 extends Interaction {
            static selector = "[data-which]";
            dynamicContent = {
                _root: {
                    "t-att-x": () => "x",
                },
            };
        }

        const { core } = await startInteraction([Test, Test2], TemplateTest);
        expect(core.interactions).toHaveLength(3);
        const subEls = queryAll(".test [data-which][x=x]");
        await click(subEls[1]);
        await click(subEls[0]);
        expect.verifySteps(["two", "one"]);
        core.stopInteractions();
        expect(queryFirst(".test [data-which]")).toBe(null);
        await click(subEls[0]);
        expect.verifySteps([]);
    });

    test("can neutralize cleanup of rendered template by setting removeOnClean to false", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.renderAt(
                    "web.testRenderAt",
                    {},
                    this.el,
                    "beforeend",
                    undefined,
                    false,
                );
            }
        }

        const { core } = await startInteraction([Test], TemplateTest);
        expect(core.interactions).toHaveLength(1);
        expect(queryFirst(".test .rendered")).toBeInstanceOf(HTMLElement);
        core.stopInteractions();
        expect(queryFirst(".test .rendered")).toBeInstanceOf(HTMLElement);
    });

    function checkOrder(position) {
        test(`order is preserved when inserting ${position} of an element`, async () => {
            class Test extends Interaction {
                static selector = ".test";
                dynamicContent = {
                    "[data-which]": {
                        "t-on-click": (ev) => expect.step(ev.target.dataset.which),
                    },
                };
                setup() {
                    const els = this.renderAt(
                        "web.TestSubInteraction1",
                        {
                            first: "one",
                            second: "two",
                        },
                        this.el.querySelector("span"),
                        position,
                        (els) => {
                            expect(els).toHaveLength(2);
                            for (const el of els) {
                                expect.step(`callback on ${el.dataset.which}`);
                            }
                        },
                    );
                    expect(els).toHaveLength(2);
                    for (const el of els) {
                        expect.step(`result has ${el.dataset.which}`);
                    }
                }
            }

            const { core } = await startInteraction([Test], TemplateTest);
            expect(core.interactions).toHaveLength(1);
            const subEls = queryAll(".test [data-which]");
            expect(subEls).toHaveLength(2);
            expect(subEls[0]).toHaveAttribute("data-which", "one");
            expect(subEls[1]).toHaveAttribute("data-which", "two");
            await click(subEls[1]);
            await click(subEls[0]);
            expect.verifySteps([
                "callback on one",
                "callback on two",
                "result has one",
                "result has two",
                "two",
                "one",
            ]);
            core.stopInteractions();
            expect(queryFirst(".test [data-which]")).toBe(null);
            await click(subEls[0]);
            expect.verifySteps([]);
        });
    }
    checkOrder("beforebegin");
    checkOrder("afterbegin");
    checkOrder("beforeend");
    checkOrder("afterend");

    function checkCallbackArrayIsNotReversedLater(position) {
        test(`the array given to the callback keeps DOM order (${position})`, async () => {
            class Test extends Interaction {
                static selector = ".test";
                setup() {
                    /** @type {any} */
                    let kept;
                    this.renderAt(
                        "web.TestSubInteraction1",
                        { first: "one", second: "two" },
                        this.el.querySelector("span"),
                        position,
                        (els) => (kept = els),
                    );
                    expect.step(kept.map((el) => el.dataset.which).join(","));
                }
            }
            await startInteraction([Test], TemplateTest);
            const inDom = queryAll(".test [data-which]").map((el) => el.dataset.which);
            expect(inDom).toEqual(["one", "two"]);
            expect.verifySteps(["one,two"]);
        });
    }
    checkCallbackArrayIsNotReversedLater("afterbegin");
    checkCallbackArrayIsNotReversedLater("afterend");
});

describe("locked", () => {
    test("locked disable any further execution while already executing", async () => {
        let started = 0;
        let finished = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                button: {
                    "t-on-click": this.locked(this.onClickLong),
                },
            };
            async onClickLong() {
                started++;
                await new Promise((resolve) => setTimeout(resolve, 5000));
                finished++;
            }
        }
        await startInteraction(Test, TemplateTestDoubleButton);
        for (const buttonEl of queryAll("button")) {
            await click(buttonEl);
        }
        expect(started).toBe(1);
        expect(finished).toBe(0);
        await advanceTime(10000);
        expect(started).toBe(1);
        expect(finished).toBe(1);
    });

    test("locked doesn't add a loading icon if not required", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                button: {
                    "t-on-click": this.locked(this.onClickLong),
                },
            };
            async onClickLong() {
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }
        }
        await startInteraction(Test, TemplateTestDoubleButton);
        expect(queryFirst("span")).toBe(null);
        await click("button");
        await advanceTime(500);
        expect(queryFirst("span")).toBe(null);
    });

    test("locked add a loading icon when the execution takes more than 400ms", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                button: {
                    "t-on-click": this.locked(this.onClickLong, true),
                },
            };
            async onClickLong() {
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }
        }
        await startInteraction(Test, TemplateTestDoubleButton);
        expect(queryFirst("span")).toBe(null);
        await click("button");
        await advanceTime(500);
        expect(queryFirst("span")).not.toBe(null);
    });

    test("locked automatically binds functions", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                button: { "t-on-click": this.locked(this.sayValue) },
            };
            setup() {
                this.value = "value";
            }
            sayValue() {
                return Promise.resolve(expect.step(this.value));
            }
        }
        await startInteraction(Test, TemplateTestDoubleButton);
        expect.verifySteps([]);
        await click("button");
        expect.verifySteps(["value"]);
    });

    test("locked event handler runs through protect", async () => {
        installProtect();
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.locked(() => {
                        expect.step("done");
                    }),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["updateContent"]);
        await click(queryOne(".test"));
        expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
    });
});

describe("debounced (1)", () => {
    let core;
    let testEl;
    /** @type {() => void} */
    let cancel;
    beforeEach(async () => {
        patchWithCleanup(Colibri.prototype, {
            updateContent() {
                expect.step("updateContent");
                super.updateContent();
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => this.debouncedFn() },
            };
            setup() {
                this.debouncedFn = this.debounced(this.doSomething, 500);
            }
            doSomething() {
                expect.step("done");
            }
        }
        ({ core } = await startInteraction(Test, TemplateTest));
        expect.verifySteps(["updateContent"]);
        cancel = getInteraction(core, Test).debouncedFn.cancel;
        testEl = queryOne(".test");
    });

    test("debounced event handler delays and groups calls", async () => {
        await click(testEl);
        expect.verifySteps([]);
        await advanceTime(250);
        expect.verifySteps([]);
        await click(testEl);
        expect.verifySteps([]);
        await advanceTime(250);
        expect.verifySteps([]);
        await click(testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
    });

    test("debounced event handler considers distant events as distinct", async () => {
        await click(testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
        await click(testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
    });

    test("debounced event handler cancels events on destroy", async () => {
        await click(testEl);
        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps([]);
    });

    test("can cancel debounced event handler", async () => {
        await click(testEl);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
        await click(testEl);
        await click(testEl);
        cancel();
        await advanceTime(500);
        expect.verifySteps([]);
    });
});

describe("debounced (2)", () => {
    test("debounced with long willstart", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const fn = this.debounced(() => expect.step("debounced"), 50);
                fn();
            }
            async willStart() {
                expect.step("willstart");
                await new Promise((resolve) => {
                    setTimeout(resolve, 100);
                });
            }
            start() {
                expect.step("start");
            }
            updateContent() {
                expect.step("updatecontent");
                super.updateContent();
            }
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["willstart", "debounced", "start"]);
    });

    test("debounced is not called if the interaction is destroyed in the meantime", async () => {
        freezeTime();
        /** @type {number} */
        let debounceTimer;

        class Test extends Interaction {
            static selector = ".test";
            setup() {
                debounceTimer = Date.now() + 50;
                const fn = this.debounced(() => expect.step("debounced"), 50);
                fn();
            }
            updateContent() {
                expect.step("updatecontent");
                super.updateContent();
            }
            async willStart() {
                expect.step("willstart");
                await new Promise((resolve) => {
                    setTimeout(resolve, 100);
                });
            }
            start() {
                expect.step("start");
            }
            destroy() {
                expect.step("destroy");
            }
        }
        const { core } = await startInteraction(Test, TemplateTest, {
            waitForStart: false,
        });
        expect.verifySteps(["willstart"]);
        const now = Date.now();
        if (now > debounceTimer) {
            console.log("code took too long...");
        }
        const step = (debounceTimer - now) / 2;
        await advanceTime(step);
        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps(["destroy"]);
        await advanceTime(500);
        expect.verifySteps([]);
    });

    test("debounced forwards arguments", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.debounced((ev) => expect.step(ev.type), 500),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        await advanceTime(25);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["click"]);
    });

    test("debounced requires .withTarget to access currentTarget", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.debounced((ev) => {
                        expect(ev.currentTarget).toBe(null);
                        expect.step(ev.type);
                    }, 500),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        await advanceTime(25);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["click"]);
    });

    test("debounced receives currentTarget when using .withTarget", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click.withTarget": this.debounced((ev, el) => {
                        expect(el.tagName).toBe("DIV");
                        expect.step(ev.type);
                    }, 500),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        await advanceTime(25);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["click"]);
    });

    test("debounced handles async event handler", async () => {
        const def = new Deferred();
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": this.debounced(async () => {
                        await def;
                        clicked++;
                    }, 100),
                    "t-att-x": () => clicked.toString(),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        await click("span");
        await advanceTime(100);
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        def.resolve();
        await animationFrame();
        expect(clicked).toBe(1);
        expect("span").toHaveAttribute("x", "1");
    });

    test("debounced event handler runs through protect", async () => {
        installProtect();
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.debounced(() => {
                        expect.step("done");
                    }, 100),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["updateContent"]);
        await click(queryOne(".test"));
        expect.verifySteps([]);
        await advanceTime(100);
        expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
    });
});

describe("throttled_for_animation (1)", () => {
    let core;
    let testEl;
    /** @type {() => void} */
    let cancel;
    (beforeEach(async () => {
        patchWithCleanup(Colibri.prototype, {
            updateContent() {
                expect.step("updateContent");
                super.updateContent();
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => this.throttle() },
            };
            setup() {
                this.throttle = this.throttled(this.doSomething);
            }
            doSomething() {
                expect.step("done");
            }
        }
        ({ core } = await startInteraction(Test, TemplateTest));
        expect.verifySteps(["updateContent"]);
        cancel = getInteraction(core, Test).throttle.cancel;
        testEl = queryOne(".test");
    }),
        test("throttled event handler executes call right away", async () => {
            await click(testEl);
            expect.verifySteps(["done", "updateContent"]);
        }),
        test("throttled event handler delays further calls", async () => {
            await click(testEl);
            await click(testEl);
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps([]);
        }),
        test("throttled event handler delays and groups further calls", async () => {
            await click(testEl);
            await click(testEl);
            await click(testEl);
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps([]);
        }),
        test("throttled event handler cancels delayed calls", async () => {
            await click(testEl);
            await click(testEl);
            await click(testEl);
            expect.verifySteps(["done", "updateContent"]);
            core.stopInteractions();
            expect.verifySteps([]);
            await animationFrame();
            expect.verifySteps([]);
        }));

    test("can cancel throttled event handler", async () => {
        await click(testEl);
        expect.verifySteps(["done", "updateContent"]);
        await click(testEl);
        await click(testEl);
        cancel();
        expect.verifySteps([]);
    });
});

describe("throttled_for_animation (2)", () => {
    test("throttled functions work with long willstart", async () => {
        patchWithCleanup(Colibri.prototype, {
            updateContent() {
                expect.step("updatecontent");
                super.updateContent();
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = { _root: { "t-att-a": () => "b" } };
            setup() {
                const fn = this.throttled(() => expect.step("throttle"));
                fn();
            }
            async willStart() {
                expect.step("willstart");
                await new Promise((resolve) => {
                    setTimeout(resolve, 100);
                });
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(Test, TemplateTest, { waitForStart: false });
        expect.verifySteps(["throttle", "willstart"]);
        await advanceTime(150);
        expect.verifySteps(["updatecontent", "start"]);
    });

    test("throttled_for_animation forwards arguments", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": this.throttled((ev) => expect.step(ev.type)) },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        expect.verifySteps(["click"]);
    });

    test("throttledForAnimation does not require .withTarget to access currentTarget", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.throttled((ev) => {
                        expect(ev.currentTarget.tagName).toBe("DIV");
                        expect.step(ev.type);
                    }),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        expect.verifySteps(["click"]);
    });

    test("throttledForAnimation receives currentTarget when using .withTarget", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click.withTarget": this.throttled((ev, el) => {
                        expect(el.tagName).toBe("DIV");
                        expect.step(ev.type);
                    }),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        await click(".test");
        expect.verifySteps(["click"]);
    });

    test("throttled handles async event handler", async () => {
        const def = new Deferred();
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": this.throttled(async () => {
                        await def;
                        clicked++;
                    }),
                    "t-att-x": () => clicked.toString(),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        await click("span");
        await advanceTime(100);
        expect(clicked).toBe(0);
        expect("span").toHaveAttribute("x", "0");
        def.resolve();
        await animationFrame();
        expect(clicked).toBe(1);
        expect("span").toHaveAttribute("x", "1");
    });

    test("throttled event handler runs through protect", async () => {
        installProtect();
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.throttled(() => {
                        expect.step("done");
                    }),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps(["updateContent"]);
        const testEl = queryOne(".test");
        await click(testEl);
        await click(testEl);
        expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
        await animationFrame();
        expect.verifySteps(["protect", "done", "unprotect", "updateContent"]);
        await animationFrame();
        expect.verifySteps([]);
    });
});

describe("patching", () => {
    test("patching keeps 'this' for an entry written as a method reference", async () => {
        class Base extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": this.onClick,
                    "t-att-animal": this.getAnimal,
                },
            };
            setup() {
                this.name = "colibri";
            }
            onClick() {
                expect.step(`click:${this?.name}`);
            }
            getAnimal() {
                return this?.name;
            }
        }
        patch(Base.prototype, {
            setup() {
                super.setup();
                patchDynamicContent(this.dynamicContent, {
                    _root: {
                        "t-on-click": (ev, oldFn) => {
                            oldFn(ev);
                            expect.step("click:patch");
                        },
                        "t-att-animal": (el, old) => `${old}!`,
                    },
                });
            },
        });
        await startInteraction(Base, TemplateTest);
        expect(".test").toHaveAttribute("animal", "colibri!");
        await click(".test");
        expect.verifySteps(["click:colibri", "click:patch"]);
    });

    test("'this' is kept through patches", async () => {
        class Base extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click": () => this.value++,
                    "t-att-value": () => this.value,
                    "t-att-class": () => ({
                        base: true,
                    }),
                },
            };
            setup() {
                this.value = 10;
            }
        }
        patch(Base.prototype, {
            setup() {
                super.setup();
                patchDynamicContent(this.dynamicContent, {
                    span: {
                        "t-att-value": (el, old) => old * 2 + this.value,
                        "t-att-class": () => ({
                            big: this.value >= 50,
                        }),
                    },
                });
            },
        });
        patch(Base.prototype, {
            setup() {
                super.setup();
                patchDynamicContent(this.dynamicContent, {
                    span: {
                        "t-on-click": () => (this.value *= 5),
                        "t-att-value": (el, old) => old * 10 - this.value,
                        "t-att-class": () => ({
                            bigger: this.value >= 100,
                        }),
                    },
                });
            },
        });
        const { core } = await startInteraction(Base, TemplateTest);
        const interaction = getInteraction(core, Base);
        expect(interaction.value).toBe(10);
        expect("span").toHaveAttribute("value", "290");
        expect("span").toHaveClass("base");
        expect("span").not.toHaveClass(["big", "bigger"]);
        await click("span");
        expect(interaction.value).toBe(50);
        expect("span").toHaveAttribute("value", "1450");
        expect("span").toHaveClass(["base", "big"]);
        expect("span").not.toHaveClass("bigger");
        await click("span");
        expect(interaction.value).toBe(250);
        expect("span").toHaveAttribute("value", "7250");
        expect("span").toHaveClass(["base", "big", "bigger"]);
    });
});

describe("teardown and error routing", () => {
    test("a cleanup registered before a mountComponent still runs on destroy", async () => {
        class Child extends Component {
            static template = xml`<span class="child"/>`;
            static props = {};
        }
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => expect.step("cleanup A"));
                this.mountComponent(this.el, Child);
                this.registerCleanup(() => expect.step("cleanup C"));
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        await animationFrame();
        core.stopInteractions();
        expect.verifySteps(["cleanup C", "cleanup A"]);
    });

    test("interactions inside an inserted element are stopped with their host", async () => {
        class Child extends Interaction {
            static selector = ".child";
            destroy() {
                expect.step("child destroyed");
            }
        }
        class Parent extends Interaction {
            static selector = ".test";
            static selectorHas = ".flag";
            setup() {
                const el = document.createElement("div");
                el.className = "child";
                this.insert(el);
            }
        }
        const { core } = await startInteraction(
            [Parent, Child],
            `<div class="test"><span class="flag"></span></div><div class="other"></div>`,
        );
        expect(core.interactions).toHaveLength(2);
        queryOne(".flag").remove();
        core.stopInteractions(queryOne(".other"));
        expect.verifySteps(["child destroyed"]);
        expect(core.interactions).toHaveLength(0);
    });

    test("an async .noUpdate handler is awaited and its error reported", async () => {
        const errors = [];
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click.noUpdate": async () => {
                        expect.step("handler start");
                        await Promise.resolve();
                        throw new Error("async boom");
                    },
                },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        core.reportError = (error) => errors.push(error);
        await click(".test");
        await animationFrame();
        expect.verifySteps(["handler start"]);
        expect(errors.map((e) => e.message)).toEqual(["async boom"]);
    });

    test("a locked() handler failure reaches the error channel", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.onClick = this.locked(async () => {
                    throw new Error("locked boom");
                });
            }
            dynamicContent = {
                _root: { "t-on-click": (ev) => this.onClick(ev) },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const errors = [];
        core.reportError = (error) => errors.push(error);
        await click(".test");
        await animationFrame();
        await animationFrame();
        expect(errors.map((e) => e.message)).toEqual(["locked boom"]);
    });

    test("a debounced handler failure reaches the error channel", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.onClick = this.debounced(async () => {
                    throw new Error("debounced boom");
                }, 0);
            }
            dynamicContent = {
                _root: { "t-on-click": (ev) => this.onClick(ev) },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const errors = [];
        core.reportError = (error) => errors.push(error);
        await click(".test");
        await animationFrame();
        await animationFrame();
        await animationFrame();
        expect(errors.map((e) => e.message)).toEqual(["debounced boom"]);
    });
});

describe("dynamic attributes", () => {
    test("t-att-class keys that appear later are restored on destroy", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-att-class": () => (this.phase === 0 ? { a: true } : { b: true }),
                },
            };
            setup() {
                this.phase = 0;
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const el = queryOne(".test");
        expect(el.className).toBe("test a");
        getInteraction(core, Test).phase = 1;
        core.interactions[0].updateContent();
        expect(el.className).toBe("test a b");
        core.stopInteractions();
        expect(el.className).toBe("test");
    });

    test("t-att-class tolerates multi-space class keys", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-att-class": () => ({ "x  y": true }) },
            };
        }
        await startInteraction(Test, `<div class="test"></div>`);
        expect(queryOne(".test").className).toBe("test x y");
    });

    test("selector-bound listeners are detached when their node departs, even when addListener forwards only its documented arguments", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".item": { "t-on-click": () => expect.step("clicked") },
            };
        }
        patchWithCleanup(Colibri.prototype, {
            addListener(nodes, event, fn, options) {
                return super.addListener(nodes, event, fn, options);
            },
        });
        const { core } = await startInteraction(
            Test,
            `<div class="test"><span class="item"></span></div>`,
        );
        await click(".item");
        expect.verifySteps(["clicked"]);
        queryOne(".test span").classList.remove("item");
        core.interactions[0].updateContent();
        await click(".test span");
        expect.verifySteps([]);
    });
});

describe("lifecycle edge cases", () => {
    test("being destroyed mid-willStart still settles the start promise", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            async willStart() {
                await this.waitFor(def);
                expect.step("willStart resumed");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await animationFrame();
        expect(core.interactions).toHaveLength(1);
        core.stopInteractions();
        def.resolve();

        let settled = false;
        core.isReady.then(
            () => (settled = true),
            () => (settled = true),
        );
        for (let i = 0; i < 10; i++) {
            await animationFrame();
        }
        expect(settled).toBe(true);
        expect.verifySteps([]);
    });

    test("an async start() that rejects reaches the error channel", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            async start() {
                await def;
                throw new Error("boom in async start");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        patchWithCleanup(core, {
            reportError(error) {
                if (!(error instanceof Error)) {
                    throw error;
                }
                expect.step(`reported:${error.message}`);
            },
        });
        def.resolve();
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["reported:boom in async start"]);
    });

    test("isReady waits for an async start(), it does not race it", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            async start() {
                await def;
                expect.step("start finished");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        let ready = false;
        core.isReady.then(() => (ready = true));
        for (let i = 0; i < 5; i++) {
            await animationFrame();
        }
        expect(ready).toBe(false);
        expect.verifySteps([]);

        def.resolve();
        await core.isReady;
        expect.verifySteps(["start finished"]);
    });

    test("a start() that never settles is released by teardown, not held forever", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            async start() {
                await this.waitFor(def);
                expect.step("never reached");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await animationFrame();
        core.stopInteractions();
        def.resolve();
        await core.isReady;
        expect.verifySteps([]);
    });

    test("a willStart throwing synchronously still tears the interaction down", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => expect.step("cleaned up"));
            }
            willStart() {
                throw new Error("boom");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom");
        expect.verifySteps(["cleaned up"]);
        expect(core.interactions).toHaveLength(0);
        await animationFrame();
        expect.verifyErrors([/boom/]);
    });

    test("a willStart that fails after teardown still reaches the error channel", async () => {
        const def = new Deferred();
        class Test extends Interaction {
            static selector = ".test";
            async willStart() {
                await def;
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await animationFrame();
        patchWithCleanup(core, {
            reportError(error) {
                if (!(error instanceof Error)) {
                    throw error;
                }
                expect.step(`reported:${error.message}`);
            },
        });
        core.stopInteractions();
        def.reject(new Error("boom"));
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["reported:boom"]);
    });

    test("a selector named like an Object prototype key stays a CSS selector", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                toString: { "t-att-data-x": () => "hit" },
            };
        }
        await startInteraction(Test, `<div class="test"><tostring></tostring></div>`);
        expect("tostring").toHaveAttribute("data-x", "hit");
    });

    test("_window still resolves when the document has no default view", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _window: { "t-on-resize": () => expect.step("resized") },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const detached = document.implementation.createHTMLDocument();
        detached.body.innerHTML = `<div class="test"></div>`;
        expect(detached.defaultView).toBe(null);
        await core.startInteractions(/** @type {any} */ (detached.body));
        const started = core.interactions.at(-1);
        expect(started.interaction.el.ownerDocument).toBe(detached);
        expect([...started.dynamicNodes.get("_window")]).toHaveLength(1);
        window.dispatchEvent(new Event("resize"));
        await animationFrame();
        expect.verifySteps(["resized", "resized"]);
    });

    test("a cleanup that registers another cleanup terminates", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => {
                    expect.step("outer");
                    this.registerCleanup(() => expect.step("inner"));
                });
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        core.stopInteractions();
        expect.verifySteps(["outer", "inner"]);
    });

    test("two selectors sharing one handler function detach independently", async () => {
        class Test extends Interaction {
            static selector = ".test";
            onHit() {
                expect.step("hit");
            }
            dynamicContent = {
                ".a": { "t-on-click": this.onHit },
                ".b": { "t-on-click": this.onHit },
            };
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><span class="a x"></span><span class="b y"></span></div>`,
        );
        await click(".x");
        await click(".y");
        expect.verifySteps(["hit", "hit"]);
        queryOne(".x").classList.remove("a");
        core.interactions[0].updateContent();
        await click(".x");
        expect.verifySteps([]);
        await click(".y");
        expect.verifySteps(["hit"]);
    });

    test("destroying an inserted host does not stop unrelated interactions", async () => {
        class Bystander extends Interaction {
            static selector = ".bystander";
            destroy() {
                expect.step("bystander destroyed");
            }
        }
        class Host extends Interaction {
            static selector = ".test";
            setup() {
                const el = document.createElement("div");
                el.className = "child";
                this.insert(el);
            }
        }
        const { core } = await startInteraction(
            [Host, Bystander],
            `<div class="test"></div><div class="bystander"></div>`,
        );
        core.stopInteractions(queryOne(".test"));
        expect.verifySteps([]);
        expect(core.interactions).toHaveLength(1);
        core.stopInteractions();
        expect.verifySteps(["bystander destroyed"]);
    });

    test("inserting adds no page-wide selectorHas re-evaluation of its own", async () => {
        const run = async (hostInserts) => {
            class Fragile extends Interaction {
                static selector = ".fragile";
                static selectorHas = ".flag";
                destroy() {
                    expect.step("fragile destroyed");
                }
            }
            class Host extends Interaction {
                static selector = ".test";
                setup() {
                    if (hostInserts) {
                        const el = document.createElement("div");
                        el.className = "child";
                        this.insert(el);
                    }
                }
            }
            const { core } = await startInteraction(
                [Host, Fragile],
                `<div class="test"></div><div class="fragile"><i class="flag"></i></div>`,
            );
            queryOne(".flag").remove();
            core.stopInteractions(queryOne(".test"));
            const stopped = core.interactions.length;
            core.stopInteractions();
            return stopped;
        };
        expect(await run(false)).toBe(await run(true));
        expect.verifySteps(["fragile destroyed", "fragile destroyed"]);
    });

    test("a throwing interaction destroy still marks the colibri destroyed", async () => {
        class Test extends Interaction {
            static selector = ".test";
            destroy() {
                throw new Error("destroy boom");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const colibri = core.interactions[0];
        expect(() => core.stopInteractions()).toThrow();
        expect(colibri.isDestroyed).toBe(true);
        expect(() => colibri.destroy()).not.toThrow();
    });

    test("t-att-style keys that appear later are restored on destroy", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-att-style": () =>
                        this.phase === 0 ? { color: "red" } : { "z-index": "5" },
                },
            };
            setup() {
                this.phase = 0;
            }
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test" style="color: blue;"></div>`,
        );
        const el = queryOne(".test");
        expect(el.style.color).toBe("red");
        getInteraction(core, Test).phase = 1;
        core.interactions[0].updateContent();
        expect(el.style.zIndex).toBe("5");
        core.stopInteractions();
        expect(el.style.color).toBe("blue");
        expect(el.style.zIndex).toBe("");
    });
});

describe("restoring on destroy", () => {
    test("a node that left the selector's match set is restored too", async () => {
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                _target: { "t-att-class": () => ({ marked: true }) },
            };
            setup() {
                Object.assign(this.dynamicSelectors, {
                    _target: () => this.target,
                });
                this.target = this.el.querySelector(".a");
            }
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><span class="a"></span><span class="b"></span></div>`,
        );
        expect(".a").toHaveClass("marked");
        getInteraction(core, Test).target = queryOne(".b");
        core.interactions[0].updateContent();
        expect(".b").toHaveClass("marked");
        core.stopInteractions();
        expect(queryOne(".a").className).toBe("a");
        expect(queryOne(".b").className).toBe("b");
    });

    test("a t-out node that left the match set is restored too", async () => {
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                _target: { "t-out": () => "replaced" },
            };
            setup() {
                Object.assign(this.dynamicSelectors, {
                    _target: () => this.target,
                });
                this.target = this.el.querySelector(".a");
            }
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test"><span class="a">first</span><span class="b">second</span></div>`,
        );
        expect(queryOne(".a").textContent).toBe("replaced");
        getInteraction(core, Test).target = queryOne(".b");
        core.interactions[0].updateContent();
        core.stopInteractions();
        expect(queryOne(".a").textContent).toBe("first");
        expect(queryOne(".b").textContent).toBe("second");
    });

    test("a failing waitForTimeout callback is reported, not left uncaught", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.waitForTimeout(() => {
                    throw new Error("timeout boom");
                }, 10);
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const errors = [];
        core.reportError = (error) => errors.push(error);
        await advanceTime(20);
        expect(errors.map((e) => e.message)).toEqual(["timeout boom"]);
    });
});

describe("once listeners", () => {
    test("a fired once-listener stops being tracked", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: {
                    "t-on-click": () => {
                        this.addListener(this.el, "custom", () => {}, { once: true });
                    },
                },
            };
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`);
        const colibri = core.interactions[0];
        const el = queryOne(".test");
        const cycle = async () => {
            await click(".test");
            el.dispatchEvent(new Event("custom"));
        };
        await cycle();
        const settled = colibri.cleanups.length;
        for (let i = 0; i < 5; i++) {
            await cycle();
        }
        await animationFrame();
        expect(colibri.cleanups).toHaveLength(settled);
        expect(
            colibri.listenerRecords.filter((r) => r.event === "custom"),
        ).toHaveLength(0);
    });
});

describe("directive validation", () => {
    test("a t-att definition that is not callable is rejected where it is declared", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-att-class": { "some-class": true } },
            };
        }
        await expect(
            startInteraction(Test, `<div class="test"></div>`),
        ).rejects.toThrow(
            "'t-att-class' expects a function, got object (selector '_root' in interaction 'Test')",
        );
        await animationFrame();
        expect.verifyErrors([/'t-att-class' expects a function/]);
    });

    test("a t-out definition that is not callable is rejected too", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-out": "some text" },
            };
        }
        await expect(
            startInteraction(Test, `<div class="test"></div>`),
        ).rejects.toThrow("'t-out' expects a function, got string");
        await animationFrame();
        expect.verifyErrors([/'t-out' expects a function/]);
    });
});

describe("aborting a failed start", () => {
    test("a throwing start() detaches the listeners it had already bound", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-on-click": () => expect.step("clicked") },
            };
            start() {
                throw new Error("boom in start");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom in start");
        expect(core.interactions).toHaveLength(0);
        await click(".test");
        await animationFrame();
        expect.verifySteps([]);
        await animationFrame();
        expect.verifyErrors([/boom in start/]);
    });

    test("a rejecting willStart() undoes what setup() did", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.registerCleanup(() => expect.step("cleanup"));
                const el = document.createElement("p");
                el.className = "inserted";
                this.insert(el);
            }
            async willStart() {
                throw new Error("boom in willStart");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom in willStart");
        expect.verifySteps(["cleanup"]);
        expect(".inserted").toHaveCount(0);
        await animationFrame();
        expect.verifyErrors([/boom in willStart/]);
    });

    test("an aborted start runs the interaction's own destroy()", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.handle = setInterval(() => expect.step("tick"), 1);
            }
            start() {
                throw new Error("boom in start");
            }
            destroy() {
                clearInterval(this.handle);
                expect.step("destroy");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom in start");
        expect.verifySteps(["destroy"]);
        await animationFrame();
        expect.verifyErrors([/boom in start/]);
    });

    test("a destroy() that throws on a half-started interaction is reported, not rethrown", async () => {
        expect.errors(2);
        class Test extends Interaction {
            static selector = ".test";
            start() {
                throw new Error("boom in start");
            }
            destroy() {
                throw new Error("boom in destroy");
            }
        }
        const { core } = await startInteraction(Test, `<div class="test"></div>`, {
            waitForStart: false,
        });
        await expect(core.isReady).rejects.toThrow("boom in start");
        expect(core.interactions).toHaveLength(0);
        await animationFrame();
        expect.verifyErrors([/boom in destroy/, /boom in start/]);
    });

    test("an aborted start restores the dynamic content it had applied", async () => {
        expect.errors(1);
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-att-class": () => ({ applied: true }) },
            };
            start() {
                throw new Error("boom in start");
            }
        }
        const { core } = await startInteraction(
            Test,
            `<div class="test initial"></div>`,
            { waitForStart: false },
        );
        await expect(core.isReady).rejects.toThrow("boom in start");
        expect(queryOne(".test").className).toBe("test initial");
        await animationFrame();
        expect.verifyErrors([/boom in start/]);
    });
});

describe("selectors sharing an event", () => {
    test("t-on-click and t-on-click.capture on one selector both survive a refresh", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                Object.assign(this.dynamicSelectors, {
                    _target: () =>
                        this.matching ? this.el.querySelectorAll("span") : null,
                });
                this.matching = false;
            }

            dynamicContent = {
                _root: { "t-on-mouseover": () => (this.matching = true) },
                _target: {
                    "t-on-click": () => expect.step("bubble"),
                    "t-on-click.capture": () => expect.step("capture"),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        expect.verifySteps([]);
        queryOne(".test").dispatchEvent(new MouseEvent("mouseover"));
        await animationFrame();
        await click("span");
        await animationFrame();
        expect.verifySteps(["capture", "bubble"]);
    });

    test("both listeners of a shared event are detached when their node departs", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                Object.assign(this.dynamicSelectors, {
                    _target: () =>
                        this.matching ? this.el.querySelectorAll("span") : null,
                });
                this.matching = true;
            }

            dynamicContent = {
                _root: { "t-on-mouseover": () => (this.matching = false) },
                _target: {
                    "t-on-click": () => expect.step("bubble"),
                    "t-on-click.capture": () => expect.step("capture"),
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        queryOne(".test").dispatchEvent(new MouseEvent("mouseover"));
        await animationFrame();
        await click("span");
        await animationFrame();
        expect.verifySteps([]);
        expect(core.interactions[0].listenerRecords).toHaveLength(1);
    });
});

describe("DOM effect scope", () => {
    test("setup and start run inside the scope", async () => {
        /** @type {string[]} */
        const order = [];
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                order.push("enter");
                try {
                    return super.domEffectScope(fn);
                } finally {
                    order.push("leave");
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                order.push("setup");
            }
            start() {
                order.push("start");
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(order.slice(0, 3)).toEqual(["enter", "setup", "leave"]);
        expect(order).toInclude("start");
        expect(order.filter((s) => s === "enter").length).toBe(
            order.filter((s) => s === "leave").length,
        );
    });

    test("teardown runs inside the scope", async () => {
        let destroyedInside = false;
        let inScope = 0;
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                inScope++;
                try {
                    return super.domEffectScope(fn);
                } finally {
                    inScope--;
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            destroy() {
                destroyedInside = inScope > 0;
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        core.stopInteractions();
        expect(destroyedInside).toBe(true);
    });

    test("a listener body runs inside the scope", async () => {
        let inScope = 0;
        /** @type {boolean | null} */
        let handlerInScope = null;
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                inScope++;
                try {
                    return super.domEffectScope(fn);
                } finally {
                    inScope--;
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            count = 0;
            dynamicContent = {
                span: {
                    "t-on-click": () => {
                        handlerInScope = inScope > 0;
                        this.count++;
                    },
                    "t-att-data-count": () => String(this.count),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        await click("span");
        expect(handlerInScope).toBe(true);
        expect("span").toHaveAttribute("data-count", "1");
    });

    test("writing a dynamic attribute or a t-out enters the scope", async () => {
        let entered = 0;
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                entered++;
                return super.domEffectScope(fn);
            },
        });
        class Test extends Interaction {
            static selector = ".test";
        }
        const { core } = await startInteraction(Test, TemplateTest);
        const colibri = core.interactions[0];
        const el = queryOne("span");

        let before = entered;
        colibri.applyAttr(el, "data-x", "1", {});
        expect(entered).toBe(before + 1);
        expect(el).toHaveAttribute("data-x", "1");

        before = entered;
        colibri.applyTOut(el, "hello", null);
        expect(entered).toBe(before + 1);
        expect(el).toHaveText("hello");
    });

    test("keepInHistory as a suffix opts the listener out", async () => {
        let inScope = 0;
        /** @type {boolean | null} */
        let handlerInScope = null;
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                inScope++;
                try {
                    return super.domEffectScope(fn);
                } finally {
                    inScope--;
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.keepInHistory": () => {
                        handlerInScope = inScope > 0;
                    },
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        await click("span");
        expect(handlerInScope).toBe(false);
    });

    test("keepInHistory composes with another modifier and is stripped from the event", async () => {
        let inScope = 0;
        /** @type {boolean | null} */
        let handlerInScope = null;
        let defaultPrevented = null;
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                inScope++;
                try {
                    return super.domEffectScope(fn);
                } finally {
                    inScope--;
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.prevent.keepInHistory": (ev) => {
                        handlerInScope = inScope > 0;
                        defaultPrevented = ev.defaultPrevented;
                    },
                },
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        await click("span");
        expect(handlerInScope).toBe(false);
        expect(defaultPrevented).toBe(true);
        expect(core.interactions[0].listenerRecords[0].event).toBe("click");
    });

    test("a decorator wraps the scope rather than sitting inside it", async () => {
        /** @type {string[]} */
        const order = [];
        patchWithCleanup(InteractionService.prototype, {
            domEffectScope(fn) {
                order.push("enter");
                try {
                    return super.domEffectScope(fn);
                } finally {
                    order.push("leave");
                }
            },
        });
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.prevent": () => order.push("body"),
                },
            };
        }
        await startInteraction(Test, TemplateTest);
        order.length = 0;
        await click("span");
        expect(order.slice(0, 3)).toEqual(["enter", "body", "leave"]);
    });

    test("keepInHistory passed as an option does not reach addEventListener", async () => {
        const seen = [];
        const target = document.createElement("div");
        patchWithCleanup(target, {
            addEventListener(event, handler, options) {
                seen.push(options);
                return super.addEventListener(event, handler, options);
            },
        });
        const options = { keepInHistory: true, capture: true };
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.addListener(target, "click", () => {}, options);
            }
        }
        await startInteraction(Test, TemplateTest);
        expect(seen).toHaveLength(1);
        expect("keepInHistory" in seen[0]).toBe(false);
        expect(seen[0].capture).toBe(true);
        expect(options.keepInHistory).toBe(true);
    });
});
