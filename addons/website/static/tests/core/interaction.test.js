import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { animationFrame, click, dblclick } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Colibri } from "@website/core/colibri";
import { Interaction } from "@website/core/interaction";
import { startInteraction } from "./helpers";
import { Component, onWillDestroy, xml } from "@odoo/owl";

const TemplateBase = `
    <div>
        <span>coucou</span>
    </div>`

const TemplateTest = `
    <div class="test">
        <span>coucou</span>
    </div>`

const getTemplateWithAttribute = function (attribute) {
    return `
    <div>
        <span ${attribute}">coucou</span>
    </div>`
}

describe("event handling", () => {
    test("can add a listener on a single element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on root element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                "_root:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector(".test"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on body element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                "_body:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(document.body);
        expect(clicked).toBe(true);
    });

    test("can add a listener on window element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                "_window:t-on-someevent": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        window.dispatchEvent(new Event("someevent"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on document ", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                "_document:t-on-someevent": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        window.document.dispatchEvent(new Event("someevent"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on modal element, if any", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";

            dynamicSelectors = {
                "_modal": () => this.el.closest(".modal"),
            };
            dynamicContent = {
                "_modal:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        await startInteraction(
            Test,
            `
            <div class="modal">
                <div class="test">
                    <span>coucou</span>
                </div>
            </div>`,
        );
        expect(clicked).toBe(false);
        await click(document.querySelector(".modal"));
        expect(clicked).toBe(true);
    });

    test("does not crash if no modal is found", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                "_modal": () => {
                    expect.step("check");
                    return null;
                },
            }

            dynamicContent = {
                "_modal:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked = true;
            }
        }

        await startInteraction(
            Test,
            TemplateTest,
        );
        expect.verifySteps(["check"])
        expect(clicked).toBe(false);
    });

    test("crash if a function is not provided to addListener", async () => {
        let inError = false;
        class Test extends Interaction {
            static selector = ".test";

            start() {
                try {
                    this.addListener(this.el, "click", null);
                } catch (e) {
                    inError = true;
                    expect(e.message).toBe("Invalid listener for event 'click' (received falsy value)");
                }
            }
        }
        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );

        el.querySelector(".test").click();
        expect(inError).toBe(true);
    });

    test("can add a listener on a multiple elements", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";

            dynamicContent = {
                "span:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked++;
            }
        }

        const { el } = await startInteraction(
            Test,
            `
        <div class="test">
            <span>coucou1</span>
            <span>coucou2</span>
        </div>`,
        );
        expect(clicked).toBe(0);
        for (let span of el.querySelectorAll("span")) {
            await click(span);
        }
        expect(clicked).toBe(2);
    });

    test.tags("desktop")("can add multiple listeners on a element", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click": this.doSomething,
                "span:t-on-dblclick": this.doSomething,
            };
            doSomething() {
                clicked++;
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(0);
        const span = el.querySelector("span");
        await dblclick(span);
        // dblclick = 2 clicks and 1 dblcli
        expect(clicked).toBe(3);
    });

    test("listener is cleaned up when interaction is stopped", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click": this.doSomething,
            };
            doSomething() {
                clicked++;
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(0);
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
    });

    test("listener added with addListener is cleaned up", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";

            start() {
                this.addListener("span", "click", this.doSomething);
            }
            doSomething() {
                clicked++;
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(0);
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
    });

    test("single listener added with addListener can be removed", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";

            start() {
                this.removeListener = this.addListener("span", "click", this.doSomething);
            }
            doSomething() {
                clicked++;
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(0);
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
        core.interactions[0].interaction.removeListener();
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
    });

    test("multiple listeners added with addListener can be removed", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";

            start() {
                this.removeListeners = this.addListener("span", "click", this.doSomething);
            }
            doSomething() {
                clicked++;
            }
        }

        const { el, core } = await startInteraction(
            Test,
            `
        <div class="test">
            <span>coucou</span>
            <span>hello</span>
        </div>`,
        );
        expect(clicked).toBe(0);
        const spans = el.querySelectorAll("span");
        for (let i = 0; i < spans.length; i++) {
            await click(spans[i]);
        }
        expect(clicked).toBe(2);
        core.interactions[0].interaction.removeListeners();
        for (let i = 0; i < spans.length; i++) {
            await click(spans[i]);
        }
        expect(clicked).toBe(2);
    });

    test("side effects are cleaned up in reverse order", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "_root:t-on-click": () => expect.step("click1"),
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
                this.addListener(this.el, "click", () => expect.step("click2"))
                this.registerCleanup(() => {
                    expect.step("d");
                    this.el.click();
                });
            }
            destroy() {
                this.el.click(); // check that handlers have been cleaned
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect.verifySteps(["setup", "start", "click1"]);
        core.stopInteractions();
        expect.verifySteps(["d", "click1", "click2", "c", "click1", "b", "a"]);
        el.click();
        expect.verifySteps([]);
    });

    test("listener is added between willstart and start", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click": this.onClick,
            };
            setup() {
                expect.step("setup");
            }
            async willStart() {
                await click(this.el.querySelector("span"));
                expect.step("willStart");
            }
            start() {
                expect.step("start");
            }
            onClick() {
                expect.step("click");
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        await click(el.querySelector("span"));

        expect.verifySteps(["setup", "willStart", "start", "click"]);
    });

    test("this.addListener crashes if interaction is not started", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector = ".test";

            setup() {
                this.addListener("span", "click", this.doSomething);
            }
            doSomething() {
                clicked++;
            }
        }
        let error = null;
        try {
            await startInteraction( Test,
                TemplateTest,
            );
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toInclude("this.addListener can only be called after the interaction is started");
    });


    test("dom is updated after event is dispatched", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click": this.doSomething,
                "span:t-att-data-count": () => this.n,
            };

            setup() {
                this.n = 1;
            }

            doSomething() {
                this.n++;
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        const span = el.querySelector("span");
        expect(span.dataset.count).toBe("1");
        await click(span);
        expect(span.dataset.count).toBe("2");
        await animationFrame();
        expect(span.dataset.count).toBe("2");
    });

    test("add a listener with the .stop qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click.stop": this.doSomething,
            };
            doSomething(ev) {
                clicked = true;
                expect(event.defaultPrevented).toBe(false);
                expect(event.cancelBubble).toBe(true);
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
    });

    test("add a listener with the .prevent qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click.prevent": this.doSomething,
            };
            doSomething(ev) {
                clicked = true;
                expect(event.defaultPrevented).toBe(true);
                expect(event.cancelBubble).toBe(false);
            }
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
    });

    test("add a listener with the .capture qualifier", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "strong:t-on-click": this.doStrong,
                "span:t-on-click.capture": this.doSpan,
            };
            doStrong(ev) {
                expect.step("strong");
            }
            doSpan(ev) {
                expect.step("span");
            }
        }

        const { el } = await startInteraction(
            Test,
            `
        <div class="test">
            <span><strong>coucou</strong></span>
        </div>`,
        );
        expect.verifySteps([]);
        await click(el.querySelector("strong"));
        expect.verifySteps(["span", "strong"]);
    });

    test("add a listener without the .capture qualifier", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "strong:t-on-click": this.doStrong,
                "span:t-on-click": this.doSpan,
            };
            doStrong(ev) {
                expect.step("strong");
            }
            doSpan(ev) {
                expect.step("span");
            }
        }

        const { el } = await startInteraction(
            Test,
            `
        <div class="test">
            <span><strong>coucou</strong></span>
        </div>`,
        );
        expect.verifySteps([]);
        await click(el.querySelector("strong"));
        expect.verifySteps(["strong", "span"]);
    });

    test("add a listener with the .noupdate qualifier", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click.noupdate": this.doSomething,
                "span:t-att-class": () => ({"a": clicked}),
            };
            doSomething(ev) {
                clicked = true;
                expect(event.defaultPrevented).toBe(false);
                expect(event.cancelBubble).toBe(false);
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
        expect(el.querySelector("span")).not.toHaveClass("a");
        core.interactions[0].interaction.updateContent();
        expect(el.querySelector("span")).toHaveClass("a");
    });

    test("add a listener with several qualifiers", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-on-click.noupdate.stop.prevent": this.doSomething,
                "span:t-att-class": () => ({"a": clicked}),
            };
            doSomething(ev) {
                clicked = true;
                expect(event.defaultPrevented).toBe(true);
                expect(event.cancelBubble).toBe(true);
            }
        }

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
        expect(el.querySelector("span")).not.toHaveClass("a");
        core.interactions[0].interaction.updateContent();
        expect(el.querySelector("span")).toHaveClass("a");
    });

    test("allow pseudo-classes in inline format in dynamicContent", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                ".btn:not(.off):t-on-click": this.doStuff,
            }
            doStuff() {
                expect.step("doStuff");
            }
        }

        const { el } = await startInteraction(Test, `<div class="test"><span class="btn"></span><span class="btn off"></span></div>`);
        expect.verifySteps([]);
        const btn1 = el.querySelector(".btn:not(.off)");
        const btn2 = el.querySelector(".btn.off");
        await click(btn1);
        expect.verifySteps(["doStuff"]);
        await click(btn2);
        expect.verifySteps([]);
    });
});

describe("special selectors", () => {
    test("can register a special selector", async () => {

        class Test extends Interaction {
            static selector = ".test";
            dynamicSelectors = {
                "_myselector": () => this.el.querySelector(".my-selector")
            };
            dynamicContent = {
                "_myselector:t-att-animal": () => "colibri",
            };
        }

        const { el } = await startInteraction(
            Test,
            `<div class="test"><span class="my-selector">coucou</span></div>`,
        );
        expect(el.querySelector("span").outerHTML).toBe(`<span class="my-selector" animal="colibri">coucou</span>`);
    });
});

describe("t-out", () => {
    test("can do a simple t-out", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:t-out": () => "colibri",
            };
        }

        const { el } = await startInteraction(
            Test,
            TemplateTest,
        );
        expect(el.querySelector("span").outerHTML).toBe(`<span>colibri</span>`);
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

        const { el, core } = await startInteraction(
            Test,
            TemplateTest,
        );

        expect.verifySteps(["setup", "willStart", "start"]);
        core.stopInteractions();
        expect.verifySteps(["destroy"]);
        let e = null;
        try {
            interaction.updateContent();
        } catch (_e) {
            e = _e;
        }
        expect(e.message).toBe("Cannot update content of an interaction that is not ready or is destroyed")
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

        const { core } = await startInteraction(
            Test,
            TemplateTest,
            {
                waitForStart: false,
            },
        );
        expect.verifySteps(["setup", "willStart"]);
        // destroy the interaction
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

        const { core } = await startInteraction(
            Test,
            TemplateTest,
            {
                waitForStart: false,
            },
        );
        expect.verifySteps(["willStart"]);
        let e = null;
        try {
            // trigger an update
            interaction.updateContent();
        } catch (_e) {
            e = _e;
        }
        expect(e.message).toBe("Cannot update content of an interaction that is not ready or is destroyed")

        await animationFrame();
        expect.verifySteps([]);
        def.resolve();
        await animationFrame();
        expect.verifySteps(["start"]);
    });
});

describe("miscellaneous", () => {
    test("crashes if a dynamic content element does not start with t-", async () => {
        class Test extends Interaction {
            static selector = ".test";
            dynamicContent = {
                "span:click": this.doSomething,
            };
            doSomething() {}
        }

        let error = null;
        try {
            await startInteraction(Test, `<div class="test"></div>`);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toBe(
            "Invalid directive: 'click' (should start with t-)",
        );
    });

    test("crash if dynamicContent is defined on class, not on instance", async () => {

        class Test extends Interaction {
            static selector = ".test";
            static dynamicContent = {}
        }

        let error = null;
        try {
            await startInteraction(Test, `<div class="test"></div>`);
        } catch (e) {
            error = e;
        }
        expect(error).not.toBe(null);
        expect(error.message).toBe(
            "The dynamic content object should be defined on the instance, not on the class (Test)",
        );
    });

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
        const { core } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );

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
        const { core } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );

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
        const { core } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );

        expect.verifySteps([]);
        core.stopInteractions();
        expect.verifySteps(["cleanup2", "cleanup1"]);
    });

    test("waitFor does not trigger update if interaction is not ready yet", async () => {
        class Test extends Interaction {
            static selector = ".test";

            async willStart() {
                await this.waitFor(Promise.resolve(expect.step("waitfor")));
                expect.step("willstart");
                return new Promise(resolve => {
                    setTimeout(() => {
                        expect.step("timeout");
                        resolve();
                    }, 100);
                })
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(
            Test,
            `<div class="test"></div>`,{ waitForStart: false}
        );
        expect.verifySteps(["waitfor", "willstart"]);
        await advanceTime(150);
        expect.verifySteps(["timeout", "start"]);
    });


    test("waitForTimeout does not trigger update if interaction is not ready yet", async () => {
        class Test extends Interaction {
            static selector = ".test";

            async willStart() {
                await this.waitForTimeout(() => expect.step("waitfortimeout"), 50);
                expect.step("willstart");
                return new Promise(resolve => {
                    setTimeout(() => {
                        expect.step("timeout");
                        resolve();
                    }, 100);
                })
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(
            Test,
            `<div class="test"></div>`,{ waitForStart: false}
        );
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
        const { core } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect.verifySteps([]);
        await advanceTime(50);
        expect.verifySteps(["anonymous function"]);
        await advanceTime(50);
        expect.verifySteps(["named function"]);
    });

    test("waitForAnimationFrame does not trigger update if interaction is not ready yet", async () => {
        class Test extends Interaction {
            static selector = ".test";

            async willStart() {
                await this.waitForAnimationFrame(() => expect.step("waitForAnimationFrame"));
                expect.step("willstart");
                return new Promise(resolve => {
                    setTimeout(() => {
                        expect.step("timeout");
                        resolve();
                    }, 100);
                })
            }
            start() {
                expect.step("start");
            }
        }
        await startInteraction(
            Test,
            `<div class="test"></div>`, { waitForStart: false }
        );
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
        const { core } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect.verifySteps([]);
        await animationFrame();
        expect.verifySteps(["named function", "anonymous function"]);
    });
});

describe("dynamic attributes", () => {

    // T-ATT-CLASS

    test("t-att-class can add a class ", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-class": () => ({ a: true }),
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a");
    });

    test("t-att-class can add multiple classes ", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-class": () => ({ "a b": true }),
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveClass("a b");
    });

    test("t-att-class can remove a class", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-class": () => ({ a: false }),
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("class='a'"));
        expect("span").not.toHaveClass("a");
    });

    test("t-att-class reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-class": () => ({ a: true }),
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
                "_root:t-att-class": () => ({ b: true }),
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
                "_root:t-on-click": this.toggle,
                "_root:t-att-class": () => ({ a: this.var }),
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
                "_root:t-att-class": () => ({ b: undefined }),
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
                "_root:t-on-click": this.toggle,
                "_root:t-att-class": () => ({ a: this.var, b: true, c: !this.var }),
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
                "_root:t-att-class": () => ({ b: true }),
            };
        }

        const { core, el } = await startInteraction(
            Test,
            `<div><span class="a">coucou</span></div>`,
        );
        expect(el.querySelector("span").outerHTML).toBe(
            `<span class="a b">coucou</span>`,
        );
        el.querySelector("span").classList.add("c");
        expect(el.querySelector("span").outerHTML).toBe(
            `<span class="a b c">coucou</span>`,
        );
        core.stopInteractions();
        expect(el.querySelector("span").outerHTML).toBe(
            `<span class="a c">coucou</span>`,
        );
    });

    // T-ATT-STYLE

    test("t-att-style can add a style", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-style": () => ({ color: "red" }),
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style can remove a style", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-style": () => ({ color: undefined }),
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("style='color: red;'"));
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-style": () => ({ color: "red" }),
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
                "_root:t-att-style": () => ({
                    "background-color": "black",
                    "color": "red",
                }),
            };
        }

        const { core, el } = await startInteraction(
            Test,
            `<div><span style="background-color: blue">coucou</span></div>`,
        );
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red;">coucou</span>`,
        );
        el.querySelector("span").style.setProperty("width", "50%");
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red; width: 50%;">coucou</span>`,
        );
        core.stopInteractions();
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: blue; width: 50%;">coucou</span>`,
        );
    });

    test("t-att-style restores priority on reset", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-style": () => ({
                    "background-color": "black",
                    "color": "red",
                }),
            };
        }

        const { core, el } = await startInteraction(
            Test,
            `<div><span style="background-color: blue !important">coucou</span></div>`,
        );
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red;">coucou</span>`,
        );
        el.querySelector("span").style.setProperty("width", "50%", "important");
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: black; color: red; width: 50% !important;">coucou</span>`,
        );
        core.stopInteractions();
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="background-color: blue !important; width: 50% !important;">coucou</span>`,
        );
    });

    test("t-att-style does not override existing styles", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-style": () => ({ color: "red" }),
            };
        }
        const { core } = await startInteraction(Test, getTemplateWithAttribute("style='background-color: blue;'"));
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)", color: "rgb(255, 0, 0)" });
        core.stopInteractions();
        expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
        expect("span").not.toHaveStyle({ color: "rgb(255, 0, 0)" });
    });

    test("t-att-style accept variable", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-on-click": this.toggle,
                "_root:t-att-style": () => ({ color: this.var }),
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
                "_root:t-att-style": () => ({ opacity: 1 }),
            };
        }
        await startInteraction(Test, TemplateBase);
        expect("span").toHaveStyle({ opacity: "1" });
    });

    test("t-att-style can manipulate multiple styles", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-on-click": this.toggle,
                "_root:t-att-style": () => ({ "background-color": this.b, "color": this.c }),
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
                "_root:t-att-style": () => ({ color: "red !important" }),
            };
        }
        const { el } = await startInteraction(Test, TemplateBase);
        expect(el.querySelector("span").outerHTML).toBe(
            `<span style="color: red !important;">coucou</span>`,
        );
        // await startInteraction(Test, TemplateBlueBackground);
        // expect("span").toHaveStyle({ backgroundColor: "rgb(0, 0, 255)", color: "rgb(255, 0, 0) !important" });
    });

    // T-ATT

    test("t-att-... can add an attribute", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-a": () => "b",
            };
        }
        await startInteraction(Test, TemplateTest);
        expect("span").toHaveAttribute("a", "b");
    });

    test("t-att-... can remove an attribute", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-a": () => undefined,
            };
        }
        await startInteraction(Test, getTemplateWithAttribute("a='b'"));
        expect("span").not.toHaveAttribute("a");
    });

    test("t-att-... reset at stop", async () => {
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-a": () => "b",
            };
        }
        const { core } = await startInteraction(Test, TemplateTest);
        core.stopInteractions();
        expect("span").not.toHaveAttribute("a");
    });

    test("t-att-... save previously loaded attributes", async () => {
        const c = [{}, { a: true }, { b: true }];
        const s = [{}, { "background-color": "blue" }, { "color": "red" }, {}];
        class Test extends Interaction {
            static selector = "span";
            dynamicContent = {
                "_root:t-att-class": () => c.pop(),
                "_root:t-att-style": () => s.pop(),
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
                "_root:t-att-a": (_el) => { target = _el; return "b"; },
            };
        }
        const { el } = await startInteraction(Test, TemplateBase);
        expect("span").toHaveAttribute("a", "b");
        expect(target).toBe(el.querySelector("span"));
    });
});

describe("components", () => {
    test("can insert a component with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`component`;

            setup() {
                onWillDestroy(() => isCDestroyed = true)
            }
        }

        class Test extends Interaction {
            static selector =".test";
            dynamicContent = {
                "_root:t-component": C,
            };
        }
        const { core, el } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`,
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true">component</owl-component></div>`,
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"></div>`,
        );
    });

    test("can insert a component with props with t-component", async () => {
        let isCDestroyed = false;
        class C extends Component {
            static template = xml`<p>component<span t-out="props.prop"></span></p>`;
            static props = {
                prop: { optional: true, type: String },
            };

            setup() {
                onWillDestroy(() => isCDestroyed = true)
            }
        }

        class Test extends Interaction {
            static selector =".test";
            dynamicContent = {
                "_root:t-component": () => [C, {prop: "hello"}],
            };
        }
        const { core, el } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`,
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"><p>component<span>hello</span></p></owl-component></div>`,
        );
        expect(isCDestroyed).toBe(false);
        core.stopInteractions();
        expect(isCDestroyed).toBe(true);
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"></div>`,
        );
    });

    test("can insert a component with mountComponent", async () => {
        class C extends Component {
            static template = xml`component`;
        }

        class Test extends Interaction {
            static selector = ".test";

            setup() {
                this.mountComponent(this.el, C);
            }
        }
        const { el } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`,
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true">component</owl-component></div>`,
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
                this.mountComponent(this.el, C, {prop: "with prop"});
            }
        }
        const { el } = await startInteraction(
            Test,
            `<div class="test"></div>`,
        );
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"></owl-component></div>`,
        );
        await animationFrame();
        expect(el.querySelector(".test").outerHTML).toBe(
            `<div class="test"><owl-component contenteditable="false" data-oe-protected="true"><p>component<span>with prop</span></p></owl-component></div>`,
        );
    });
});

describe("insert", () => {
    test("can insert an element", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const el = document.createElement("inserted");
                this.insert(el);
            }
        }

        const { core, el } = await startInteraction(
            Test,
            TemplateTest,
        );
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.lastElementChild);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
    });

    test("can insert an element before another one", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const spanEls = this.el.querySelectorAll("span");
                const el = document.createElement("inserted");
                this.insert(el, spanEls[1], "beforebegin");
            }
        }

        const { core, el } = await startInteraction(
            Test,
            `
        <div class="test">
            <span>first</span>
            <span>last</span>
        </div>`,
        );
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.children[1]);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
    });

    test("can insert an element after another one", async () => {
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                const spanEls = this.el.querySelectorAll("span");
                const el = document.createElement("inserted");
                this.insert(el, spanEls[0], "afterend");
            }
        }

        const { core, el } = await startInteraction(
            Test,
            `
        <div class="test">
            <span>first</span>
            <span>last</span>
        </div>`,
        );
        const testEl = el.querySelector(".test");
        let insertedEl = testEl.querySelector("inserted");
        expect(insertedEl).not.toBe(null);
        expect(insertedEl).toBe(testEl.children[1]);
        core.stopInteractions();
        insertedEl = el.querySelector("inserted");
        expect(insertedEl).toBe(null);
    });
});

describe("debounced", () => {
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
                "_root:t-on-click": () => this.debouncedFn(),
            };
            setup() {
                this.debouncedFn = this.debounced(this.doSomething, 500);
            }
            doSomething() {
                expect.step("done");
            }
        }
        const { core, el } = await startInteraction(
            Test,
            TemplateTest,
        );
        this.core = core;
        expect.verifySteps(["updateContent"]);
        this.testEl = el.querySelector(".test");
    }),

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

test("debounced with long willstart", async () => {
    class Test extends Interaction {
        static selector = ".test";

        setup() {
            const fn = this.debounced(() => expect.step("debounced"), 50);
            fn();
        }

        async willStart() {
            expect.step("willstart");
            await new Promise(resolve => {
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
    await startInteraction(
        Test,
        `
    <div class="test">
    </div>`,
    );
    expect.verifySteps(["willstart", "debounced", "start"]);
});

test("debounced is not called if interaction is destroyed in the meantime", async () => {
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
            await new Promise(resolve => {
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
    const { core } = await startInteraction(Test, `<div class="test"></div>`, { waitForStart: false });
    expect.verifySteps(["willstart"]);
    await advanceTime(25);
    expect.verifySteps([]);
    core.stopInteractions();
    expect.verifySteps(["destroy"]);
    await advanceTime(500);
    expect.verifySteps([]);
}),


describe("throttledForAnimation", () => {
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
                "_root:t-on-click": () => this.throttle(),
            };
            setup() {
                this.throttle = this.throttledForAnimation(this.doSomething);
            }
            doSomething() {
                expect.step("done");
            }
        }
        const { core, el } = await startInteraction(
            Test,
            TemplateTest,
        );
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

test("throttleForAnimation with long willstart", async () => {
    patchWithCleanup(Colibri.prototype, {
        updateContent() {
            expect.step("updatecontent");
            super.updateContent();
        },
    });

    class Test extends Interaction {
        static selector = ".test";
        dynamicContent = { "_root:t-att-a": () => "b" }

        setup() {
            const fn = this.throttledForAnimation(() => expect.step("throttle"));
            fn();
        }

        async willStart() {
            expect.step("willstart");
            await new Promise(resolve => {
                setTimeout(resolve, 100);
            });
        }
        start() {
          expect.step("start");
        }
    }
    await startInteraction(
        Test,
        `<div class="test"></div>`,
        { waitForStart: false }
    );
    expect.verifySteps(["throttle", "willstart"]);
    await advanceTime(150);
    expect.verifySteps(["updatecontent", "start"]);

});
