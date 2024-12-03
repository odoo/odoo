import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { Component, xml } from "@odoo/owl";
import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { Interaction } from "@website/core/interaction";
import { startInteraction } from "./helpers";

test("properly handles case where we have no match for wrapwrap", async () => {
    const env = await makeMockEnv();
    expect(env.services.website_core).toBe(null);

});


test("wait for translation before starting interactions", async () => {
    let flag = false;

    class Test extends Interaction {
        static selector = ".test";

        setup() {
            flag = true;
            expect("localization" in this.services).toBe(true);
        }
    }
    await startInteraction(Test, `<div class="test"></div>`);
});

test("starting interactions twice should only actually do it once", async () => {
    let n = 0;
    class Test extends Interaction {
        static selector = ".test";

        setup() {
            n++;
        }
    }

    const { core } = await startInteraction(Test, `<div class="test"></div>`);

    expect(n).toBe(1);
    core.startInteractions();
    await animationFrame();
    expect(n).toBe(1);
});

test("start interactions even if there is a crash", async () => {
    class Boom extends Interaction {
        static selector = ".test";

        setup() {
            expect.step("start boom");
            throw new Error("boom")
        }
        destroy() {
            expect.step("destroy boom");
        }
    }
    class NotBoom extends Interaction {
        static selector = ".test";

        setup() {
            expect.step("start notboom");
        }
        destroy() {
            expect.step("destroy notboom");
        }
    }

    const { core } = await startInteraction([Boom,NotBoom], `<div class="test"></div>`, { waitForStart: false});

    let e = null;
    try {
        await core.isReady;
    } catch (_e) {
        e = _e;
    }
    expect(e.message).toBe("boom");

    expect.verifySteps(["start boom", "start notboom"])
    core.stopInteractions();
    expect.verifySteps(["destroy notboom"])
});

test("interactions are stopped in reverse order", async () => {
    let n = 1;
    class Test extends Interaction {
        static selector = ".test";

        setup() {
            this.n = n++;
            expect.step(`setup ${this.n}`);
        }
        destroy() {
            expect.step(`destroy ${this.n}`);
        }
    }

    const { core } = await startInteraction(Test, `<div class="test"></div><div class="test"></div>`);
    expect.verifySteps(["setup 1", "setup 2"]);
    core.stopInteractions();
    expect.verifySteps(["destroy 2", "destroy 1"]);
});



test("can mount a component", async () => {
    class Test extends Component {
        static selector = ".test";
        static template = xml`owl component`;
    }
    const {core, el} = await startInteraction(Test, `<div class="test"></div>`);
    expect(el.querySelector(".test").innerHTML).toBe(`<owl-component contenteditable="false" data-oe-protected="true">owl component</owl-component>`);
    core.stopInteractions();
    expect(el.querySelector(".test").outerHTML).toBe(`<div class="test"></div>`);

});

test("can start interaction in specific el", async () => {
    let n = 0;
    class Test extends Interaction {
        static selector = ".test";
        dynamicContent = {
            "_root:t-att-a": () => "b",
        }

        setup() {
            n++;
        }
    }

    const { core, el } = await startInteraction(Test, `<p></p>`);

    expect(n).toBe(0);
    const p = el.querySelector("p");
    p.innerHTML = `<div class="test">hello</div>`;
    core.startInteractions(el);
    await animationFrame();
    expect(n).toBe(1);
    expect(p.innerHTML).toBe(`<div class="test" a="b">hello</div>`);
});

test("can start and stop interaction in specific el", async () => {
    let n = 0;
    class Test extends Interaction {
        static selector = ".test";

        start() {
            n++;
            this.el.dataset.start = "true";
        }
        destroy() {
            n--;
            delete this.el.dataset.start;
        }
    }

    const { core, el } = await startInteraction(Test, `
        <p>
            <span class="a test"></span>
            <span class="b"></span>
        </p>`);

    expect(n).toBe(1);
    const p = el.querySelector("p");
    expect(p).toHaveInnerHTML(`<span class="a test" data-start="true"></span> <span class="b"></span>`)
    
    p.querySelector(".b").classList.add("test");
    await core.startInteractions(p.querySelector(".b"));
    expect(n).toBe(2);
    expect(p).toHaveInnerHTML(`<span class="a test" data-start="true"></span> <span class="b test" data-start="true"></span>`)

    core.stopInteractions(p.querySelector(".b"));
    expect(n).toBe(1);
    expect(p).toHaveInnerHTML(`<span class="a test" data-start="true"></span> <span class="b test"></span>`)
});
