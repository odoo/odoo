import { expect, test, describe } from "@odoo/hoot";

import { startInteraction } from "./helpers";
import { Interaction } from "@website/core/interaction";
import { animationFrame, click } from "@odoo/hoot-dom";


// add test => if not t- => crash

describe("event handling", () => {

    test("can add a listener on a single element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector=".test";
            static dynamicContent = {
                "span:t-on-click": "doSomething"
            }
            doSomething() {
                clicked = true;
            }
        }
        
        const { el } = await startInteraction(Test, `
        <div class="test">
            <span>coucou</span>
        </div>`);
        expect(clicked).toBe(false);
        await click(el.querySelector("span"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on root element", async () => {
        let clicked = false;
        class Test extends Interaction {
            static selector=".test";
            static dynamicContent = {
                "_root:t-on-click": "doSomething"
            }
            doSomething() {
                clicked = true;
            }
        }
        
        const { el } = await startInteraction(Test, `
        <div class="test">
            <span>coucou</span>
        </div>`);
        expect(clicked).toBe(false);
        await click(el.querySelector(".test"));
        expect(clicked).toBe(true);
    });

    test("can add a listener on a multiple elements", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector=".test";
            static dynamicContent = {
                "span:t-on-click": "doSomething"
            }
            doSomething() {
                clicked++;
            }
        }
        
        const { el } = await startInteraction(Test, `
        <div class="test">
            <span>coucou1</span>
            <span>coucou2</span>
        </div>`);
        expect(clicked).toBe(0);
        for (let span of el.querySelectorAll("span")) {
            await click(span);
        }
        expect(clicked).toBe(2);
    });

    test("listener is cleaned up when interaction is stopped", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector=".test";
            static dynamicContent = {
                "span:t-on-click": "doSomething"
            }
            doSomething() {
                clicked++;
            }
        }
        
        const { el, core } = await startInteraction(Test, `
        <div class="test">
            <span>coucou</span>
        </div>`);
        expect(clicked).toBe(0);
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
    });

    test("listener added with addDomListener is cleaned up", async () => {
        let clicked = 0;
        class Test extends Interaction {
            static selector=".test";

            setup() {
                this.addDomListener("span", "click", this.doSomething)
            }
            doSomething() {
                clicked++;
            }
        }
        
        const { el, core } = await startInteraction(Test, `
        <div class="test">
            <span>coucou</span>
        </div>`);
        expect(clicked).toBe(0);
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
        core.stopInteractions();
        await click(el.querySelector("span"));
        expect(clicked).toBe(1);
    });


    test("dom is updated after event is dispatched", async () => {
        class Test extends Interaction {
            static selector=".test";
            static dynamicContent = {
                "span:t-on-click": "doSomething",
                "span:t-att-data-count": "this.n"
            }

            setup() {
                this.n = 1;
            }

            doSomething() {
                this.n++;
            }
        }
        
        const { el } = await startInteraction(Test, `
        <div class="test">
            <span>coucou</span>
        </div>`);
        const span = el.querySelector("span");
        expect(span.dataset.count).toBe("1");
        await click(span);
        expect(span.dataset.count).toBe("1");
        await animationFrame();
        expect(span.dataset.count).toBe("2");
    });
});

describe("lifecycle", () => {
    test("lifecycle methods are called in order", async () => {
        class Test extends Interaction {
            static selector=".test";
            setup() {
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
        
        const { el, core } = await startInteraction(Test, `
            <div class="test">
                <span>coucou</span>
            </div>`);

        expect.verifySteps(["setup", "willStart", "start"]);
        core.stopInteractions();
        expect.verifySteps(["destroy"]);
    });
});