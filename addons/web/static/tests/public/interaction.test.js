import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { animationFrame, click, dblclick, queryAll } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Colibri } from "@web/public/colibri";
import { Interaction } from "@web/public/interaction";
import { patchDynamicContent } from "@web/public/utils";
import { patch } from "@web/core/utils/patch";
import { startInteraction } from "./helpers";
import { Component, onWillDestroy, xml } from "@odoo/owl";

describe.current.tags("interaction_dev");

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
        const { el } = await startInteraction(Test, TemplateTestDoubleSpan);
        expect(clicked).toBe(0);
        const spans = el.querySelectorAll("span");
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
    });

    test.tags("desktop")("can add multiple listeners on an element", async () => {
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
        expect(clicked).toBe(3); // event dblclick = click + click + dblclick
    });

    test("can use addListener on HTMLCollection", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.addListener(this.el.querySelectorAll("span"), "click", () => clicked++);
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
                const spanEl = this.el.contentDocument.createElement("span");
                spanEl.textContent = "abc";
                this.el.contentDocument.body.appendChild(spanEl);
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
                const spanEl = this.el.contentDocument.createElement("span");
                spanEl.textContent = "abc";
                this.el.contentDocument.body.appendChild(spanEl);
                const spanEls = this.el.contentDocument.querySelectorAll("span");
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
        const { el } = await startInteraction(Test, TemplateTest);
        console.log(el);
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

    test("can refresh listeners", async () => {
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
                        this.refreshListeners();
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
        `
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
            </div>`
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
            </div>`
        );
        expect("span").toHaveAttribute("animal", "colibri");
    });
});

describe("removing listeners", () => {
    test("listener added with addListener is cleaned up", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                this.addListener(this.el.querySelector("span"), "click", () => clicked++);
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
                    () => clicked++
                );
            }
        }
        const { core } = await startInteraction(Test, TemplateTest);
        expect(clicked).toBe(0);
        await click("span");
        expect(clicked).toBe(1);
        core.interactions[0].interaction.removeListener();
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
                    () => clicked++
                );
            }
        }
        const { el, core } = await startInteraction(Test, TemplateTestDoubleSpan);
        expect(clicked).toBe(0);
        const spans = el.querySelectorAll("span");
        await click(spans[0]);
        await click(spans[1]);
        expect(clicked).toBe(2);
        core.interactions[0].interaction.removeListener();
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
                this.el.click(); // we check that event handler is not bound yet
                this.registerCleanup(() => expect.step("a"));
                this.registerCleanup(() => {
                    expect.step("b");
                    this.el.click();
                });
            }
            start() {
                expect.step("start");
                this.el.click(); // check that event handler is bound
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
                this.el.click(); // check that handlers have been cleaned
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
        let inError = false;
        class Test extends Interaction {
            static selector = ".test";
            start() {
                try {
                    this.addListener(this.el, "click", null);
                } catch (e) {
                    inError = true;
                    expect(e.message).toBe("Invalid listener for event 'click' (not a function)");
                }
            }
        }
        await startInteraction(Test, TemplateTest);
        await click(".test");
        expect(inError).toBe(true);
    });

    test("this.addListener crashes if interaction is not started", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.addListener(this.el.querySelector("span"), "click", () => clicked++);
            }
        }
        let error = null;
        try {
            await startInteraction(Test, TemplateTest);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toInclude(
            "this.addListener can only be called after the interaction is started"
        );
    });

    test("cannot update content while updating content", async () => {
        let update = false;
        let interaction = null;
        let error = null;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-att-a": () => {
                        if (update) {
                            try {
                                this.updateContent();
                            } catch (e) {
                                error = e;
                            }
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
        expect(error).not.toBe(null);
        expect(error.message).toInclude(
            "Updatecontent should not be called while interaction is updating"
        );
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
        const { el } = await startInteraction(Test, TemplateTest);
        const span = el.querySelector("span");
        expect(span.dataset.count).toBe("1");
        await click("span");
        expect(span.dataset.count).toBe("2");
        await animationFrame();
        expect(span.dataset.count).toBe("2");
    });

    test("crashes if a dynamic content element does not start with t-", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { click: () => {} },
            };
        }
        let error = null;
        try {
            await startInteraction(Test, TemplateTest);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toBe("Invalid directive: 'click' (should start with t-)");
    });

    test("crash if dynamicContent is defined on class, not on instance", async () => {
        class Test extends Interaction {
            static selector = ".test";
            static dynamicContent = {};
        }
        let error = null;
        try {
            await startInteraction(Test, TemplateTest);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toBe(
            "The dynamic content object should be defined on the instance, not on the class (Test)"
        );
    });

    test("crash if selector is defined on instance, not on class", async () => {
        let error = null;
        class Test extends Interaction {
            selector = ".test";
        }
        try {
            await startInteraction(Test, TemplateTest);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toBe(
            "The selector should be defined as a static property on the class Test, not on the instance"
        );
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
            </div>`
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
            </div>`
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

    test("add a listener with the .noupdate qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.noupdate": this.doSomething,
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
        core.interactions[0].interaction.updateContent();
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
                    "t-on-click.noupdate.stop.prevent": this.doSomething,
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
        core.interactions[0].interaction.updateContent();
        expect("span").toHaveClass("a");
    });

    test("add a listener does not lose 'this' with qualifiers", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: {
                    "t-on-click.noupdate.stop.prevent": this.doSomething,
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
        let e = null;
        try {
            interaction.updateContent();
        } catch (_e) {
            e = _e;
        }
        expect(e.message).toBe(
            "Cannot update content of an interaction that is not ready or is destroyed"
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
        const { core } = await startInteraction(Test, TemplateTest, { waitForStart: false });
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
        let e = null;
        try {
            interaction.updateContent();
        } catch (_e) {
            e = _e;
        }
        expect(e.message).toBe(
            "Cannot update content of an interaction that is not ready or is destroyed"
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
    });

    describe("waitForAnimationFrame", () => {
        test("waitForAnimationFrame does not trigger update if interaction is not ready yet", async () => {
            class Test extends Interaction {
                static selector = ".test";

                async willStart() {
                    await this.waitForAnimationFrame(() => expect.step("waitForAnimationFrame"));
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
        const { core } = await startInteraction(Test, getTemplateWithAttribute("class='a'"));
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
        const { core } = await startInteraction(Test, getTemplateWithAttribute("class='a b'"));
        expect("span").toHaveClass("a");
        expect("span").not.toHaveClass("b");
        core.interactions[0].interaction.updateContent();
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

        const { core, el } = await startInteraction(Test, getTemplateWithAttribute("class='a'"));
        expect("span").toHaveClass(["a", "b"]);
        el.querySelector("span").classList.add("c");
        expect("span").toHaveClass(["a", "b", "c"]);
        core.stopInteractions();
        expect("span").toHaveClass(["a", "c"]);
        expect("span").not.toHaveClass("b");
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

        const { core, el } = await startInteraction(
            Test,
            getTemplateWithAttribute("style='background-color: blue'")
        );
        expect("span").toHaveStyle({ "background-color": "rgb(0, 0, 0)", color: "rgb(255, 0, 0)" });
        el.querySelector("span").style.setProperty("width", "50%");
        expect("span").toHaveStyle({
            "background-color": "rgb(0, 0, 0)",
            color: "rgb(255, 0, 0)",
            width: "50%",
        });
        core.stopInteractions();
        expect("span").toHaveStyle({ "background-color": "rgb(0, 0, 255)", width: "50%" });
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
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

        const { core, el } = await startInteraction(
            Test,
            `<div><span style="background-color: blue !important">coucou</span></div>`
        );
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red;">coucou</span>`
        );
        el.querySelector("span").style.setProperty("width", "50%", "important");
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red; width: 50% !important;">coucou</span>`
        );
        core.stopInteractions();
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: blue !important; width: 50% !important;">coucou</span>`
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
            getTemplateWithAttribute("style='background-color: blue;'")
        );
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)", color: "rgb(255, 0, 0)" });
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
                this.var = this.var == "red" ? "blue" : "red";
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
                    "t-att-style": () => ({ "background-color": this.b, color: this.c }),
                },
            };
            setup() {
                this.b = "blue";
                this.c = "red";
            }
            toggle() {
                this.b = this.b == "red" ? "blue" : "red";
                this.c = this.c == "red" ? "blue" : "red";
            }
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)", backgroundColor: "rgb(0, 0, 255)" });
        await click("span");
        await animationFrame();
        expect("span").toHaveStyle({ color: "rgb(0, 0, 255)", backgroundColor: "rgb(255, 0, 0)" });
    });

    test("t-att-style, apply important", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                _root: { "t-att-style": () => ({ color: "red !important" }) },
            };
        }
        const { el } = await startInteraction(Test, TemplateBase);
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="color: red !important;">coucou</span>`
        );
        // await startInteraction(Test, TemplateBlueBackground);
        // expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)", color: "rgb(255, 0, 0) !important" });
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
        core.interactions[0].interaction.updateContent();
        await animationFrame();
        expect("span").toHaveClass("a");
        expect("span").toHaveClass("b");
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-... receive the target as argument", async () => {
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
        const { el } = await startInteraction(Test, TemplateBase);
        expect("span").toHaveAttribute("a", "b");
        expect(target).toBe(el.querySelector("span"));
    });

    test("t-att-... restores all values on stop", async () => {
        class Test extends Interaction {
            static selector = "div";
            dynamicContent = {
                span: { "t-att-data-animal": () => undefined },
            };
        }
        const { core, el } = await startInteraction(
            Test,
            `
            <div>
                <span data-animal="colibri">1</span>
                <span data-animal="owlet">2</span>
            </div>
        `
        );
        const spanEls = el.querySelectorAll("span");
        expect(spanEls[0].dataset.animal).toBe(undefined);
        expect(spanEls[1].dataset.animal).toBe(undefined);
        core.stopInteractions();
        expect(spanEls[0].dataset.animal).toBe("colibri");
        expect(spanEls[1].dataset.animal).toBe("owlet");
    });

    test("t-att-... restores all values on stop even if swapped", async () => {
        class Test extends Interaction {
            static selector = "div";
            dynamicContent = {
                span: { "t-att-data-animal": () => undefined },
            };
        }
        const { core, el } = await startInteraction(
            Test,
            `
            <div>
                <span data-animal="colibri">1</span>
                <span data-animal="owlet">2</span>
            </div>
        `
        );
        const spanEls = el.querySelectorAll("span");
        expect(spanEls[0].dataset.animal).toBe(undefined);
        expect(spanEls[1].dataset.animal).toBe(undefined);
        spanEls[0].parentElement.appendChild(spanEls[0]); // swap
        core.stopInteractions();
        expect(spanEls[0].dataset.animal).toBe("colibri");
        expect(spanEls[1].dataset.animal).toBe("owlet");
    });

    test("can do a simple t-out", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                span: { "t-out": () => "colibri" },
            };
        }
        const { el } = await startInteraction(Test, TemplateTest);
        expect(el.querySelector("span").outerHTML).toBe(`<span>colibri</span>`);
    });
});

describe("components", () => {
    test("can insert a component with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`component`;
            static props = {};

            setup() {
                onWillDestroy(() => (isCDestroyed = true));
            }
        }

        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-component": C },
            };
        }
        const { core, el } = await startInteraction(Test, `<div class="test"></div>`);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true">component</owl-component></div>`
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(el.querySelector(".test").outerHTML).toBe(`<div class="test"></div>`);
    });

    test("can insert a component with props with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`<p>component<span t-out="props.prop"></span></p>`;
            static props = {
                prop: { optional: true, type: String },
            };

            setup() {
                onWillDestroy(() => (isCDestroyed = true));
            }
        }

        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                _root: { "t-component": () => [C, { prop: "hello" }] },
            };
        }
        const { core, el } = await startInteraction(Test, `<div class="test"></div>`);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"><p>component<span>hello</span></p></owl-component></div>`
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(el.querySelector(".test").outerHTML).toBe(`<div class="test"></div>`);
    });

    test("can insert a component with mountComponent", async () => {
        class C extends Component {
            static template = xml`component`;
            static props = {};
        }

        class Test extends Interaction {
            static selector = ".test";

            setup() {
                this.mountComponent(this.el, C);
            }
        }
        const { el } = await startInteraction(Test, `<div class="test"></div>`);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true">component</owl-component></div>`
        );
    });

    test("can insert a component with props with mountComponent", async () => {
        class C extends Component {
            static template = xml`<p>component<span t-out="props.prop"></span></p>`;
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
        const { el } = await startInteraction(Test, `<div class="test"></div>`);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"><p>component<span>with prop</span></p></owl-component></div>`
        );
    });
});

describe("insert", () => {
    test("can insert an element after another nested", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const node = document.createElement("inserted");
                this.insert(node, this.el);
            }
        }

        const { core, el } = await startInteraction(Test, TemplateTest);
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.lastElementChild);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
    });

    test("can insert an element before another nested", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const node = document.createElement("inserted");
                this.insert(node, this.el, "afterbegin");
            }
        }
        const { core, el } = await startInteraction(Test, TemplateTest);
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.firstElementChild);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
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
        const { core, el } = await startInteraction(Test, TemplateTest);
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.children[0]);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
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
        const { core, el } = await startInteraction(Test, TemplateTest);
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.children[1]);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
    });
});

describe("renderAt", () => {
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
                    this.el
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

        const { core, el } = await startInteraction([Test, Test2], TemplateTest);
        expect(core.interactions).toHaveLength(3); // 1*Test + 2*Test2
        const testEl = el.querySelector(".test");
        const subEls = testEl.querySelectorAll("[data-which][x=x]");
        await click(subEls[1]);
        await click(subEls[0]);
        expect.verifySteps(["two", "one"]);
        core.stopInteractions();
        expect(testEl.querySelectorAll("[data-which]")).toHaveLength(0);
        await click(subEls[0]);
        expect.verifySteps([]);
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
                        }
                    );
                    expect(els).toHaveLength(2);
                    for (const el of els) {
                        expect.step(`result has ${el.dataset.which}`);
                    }
                }
            }

            const { core, el } = await startInteraction([Test], TemplateTest);
            expect(core.interactions).toHaveLength(1);
            const testEl = el.querySelector(".test");
            const subEls = testEl.querySelectorAll("[data-which]");
            expect(subEls).toHaveLength(2);
            expect(subEls[0].dataset.which).toBe("one");
            expect(subEls[1].dataset.which).toBe("two");
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
            expect(testEl.querySelectorAll("[data-which]")).toHaveLength(0);
            await click(subEls[0]);
            expect.verifySteps([]);
        });
    }
    checkOrder("beforebegin");
    checkOrder("afterbegin");
    checkOrder("beforeend");
    checkOrder("afterend");
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
        const { el } = await startInteraction(Test, TemplateTestDoubleButton);
        const buttonEls = el.querySelectorAll("button");
        for (const buttonEl of buttonEls) {
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
        const { el } = await startInteraction(Test, TemplateTestDoubleButton);
        expect(el.querySelectorAll("span")).toHaveLength(0);
        await click("button");
        await advanceTime(500);
        expect(el.querySelectorAll("span")).toHaveLength(0);
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
        const { el } = await startInteraction(Test, TemplateTestDoubleButton);
        expect(el.querySelectorAll("span")).toHaveLength(0);
        await click("button");
        await advanceTime(500);
        expect(el.querySelectorAll("span")).toHaveLength(1);
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
});

describe("debounced (1)", () => {
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
        const { core, el } = await startInteraction(Test, TemplateTest);
        this.core = core;
        expect.verifySteps(["updateContent"]);
        this.testEl = el.querySelector(".test");
    });

    test("debounced event handler delays and groups calls", async () => {
        await click(this.testEl);
        expect.verifySteps([]);
        await advanceTime(250);
        expect.verifySteps([]);
        await click(this.testEl);
        expect.verifySteps([]);
        await advanceTime(250);
        expect.verifySteps([]);
        await click(this.testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
    });

    test("debounced event handler considers distant events as distinct", async () => {
        await click(this.testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
        await click(this.testEl);
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
    });

    test("debounced event handler cancels events on destroy", async () => {
        await click(this.testEl);
        expect.verifySteps([]);
        this.core.stopInteractions();
        expect.verifySteps([]);
        await advanceTime(500);
        expect.verifySteps([]);
    });

    test("can cancel debounced event handler", async () => {
        await click(this.testEl);
        await advanceTime(500);
        expect.verifySteps(["done", "updateContent"]);
        await click(this.testEl);
        await click(this.testEl);
        this.core.interactions[0].interaction.debouncedFn.cancel();
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
        class Test extends Interaction {
            static selector = ".test";
            setup() {
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
        const { core } = await startInteraction(Test, TemplateTest, { waitForStart: false });
        expect.verifySteps(["willstart"]);
        await advanceTime(25);
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
                _root: { "t-on-click": this.debounced((ev) => expect.step(ev.type), 500) },
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
});

describe("throttled_for_animation (1)", () => {
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
                _root: { "t-on-click": () => this.throttle() },
            };
            setup() {
                this.throttle = this.throttled(this.doSomething);
            }
            doSomething() {
                expect.step("done");
            }
        }
        const { core, el } = await startInteraction(Test, TemplateTest);
        this.core = core;
        expect.verifySteps(["updateContent"]);
        this.testEl = el.querySelector(".test");
    }),
        test("throttled event handler executes call right away", async () => {
            await click(this.testEl);
            expect.verifySteps(["done", "updateContent"]);
        }),
        test("throttled event handler delays further calls", async () => {
            await click(this.testEl);
            await click(this.testEl);
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps([]);
        }),
        test("throttled event handler delays and groups further calls", async () => {
            await click(this.testEl);
            await click(this.testEl);
            await click(this.testEl);
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps(["done", "updateContent"]);
            await animationFrame();
            expect.verifySteps([]);
        }),
        test("throttled event handler cancels delayed calls", async () => {
            await click(this.testEl);
            await click(this.testEl);
            await click(this.testEl);
            expect.verifySteps(["done", "updateContent"]);
            this.core.stopInteractions();
            expect.verifySteps([]);
            await animationFrame();
            expect.verifySteps([]);
        });

    test("can cancel throttled event handler", async () => {
        await click(this.testEl);
        expect.verifySteps(["done", "updateContent"]);
        await click(this.testEl);
        await click(this.testEl);
        this.core.interactions[0].interaction.throttle.cancel();
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
});

describe("patching", () => {
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
        const interaction = core.interactions[0].interaction;
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
