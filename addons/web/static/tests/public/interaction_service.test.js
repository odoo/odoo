import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { Component, xml } from "@odoo/owl";
import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { Interaction } from "@web/public/interaction";
import { startInteraction } from "./helpers";

describe.current.tags("interaction_dev");

test("properly fallback to body when we have no match for wrapwrap", async () => {
    const env = await makeMockEnv();
    expect(env.services["public.interactions"].el).toBe(document.querySelector("body"));
});

test("wait for translation before starting interactions", async () => {
    class Test extends Interaction {
        static selector = ".test";

        setup() {
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
            throw new Error("boom");
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

    const { core } = await startInteraction([Boom, NotBoom], `<div class="test"></div>`, {
        waitForStart: false,
    });
    await expect(core.isReady).rejects.toThrow("boom");
    expect.verifySteps(["start boom", "start notboom"]);
    core.stopInteractions();
    expect.verifySteps(["destroy notboom"]);
});

test("start interactions even if there is a crash when evaluating selector", async () => {
    class Boom extends Interaction {
        static selector = "div:invalid(coucou)";

        setup() {
            expect.step("start boom");
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
    }

    const { core } = await startInteraction([Boom, NotBoom], `<div class="test"></div>`, {
        waitForStart: false,
    });

    await expect(core.isReady).rejects.toThrow(
        "Could not start interaction Boom (invalid selector: 'div:invalid(coucou)')"
    );
    expect.verifySteps(["start notboom"]);
});

test("start interactions even if there is a crash when evaluating selectorHas", async () => {
    class Boom extends Interaction {
        static selector = ".test";
        static selectorHas = "div:invalid(coucou)";

        setup() {
            expect.step("start boom");
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
    }

    const { core } = await startInteraction(
        [Boom, NotBoom],
        `<div class="test"><div></div></div>`,
        {
            waitForStart: false,
        }
    );

    await expect(core.isReady).rejects.toThrow(
        "Could not start interaction Boom (invalid selector: '.test' or selectorHas: 'div:invalid(coucou)')"
    );
    expect.verifySteps(["start notboom"]);
});

test("start interactions with selectorHas", async () => {
    class Test extends Interaction {
        static selector = ".test";
        static selectorHas = ".inner";

        start() {
            expect.step("start");
        }
    }

    const { core } = await startInteraction(
        Test,
        `
        <div class="test"><div class="inner"></div></div>
        <div class="test"><div class="not-inner"></div></div>
    `
    );
    expect(core.interactions).toHaveLength(1);
    expect.verifySteps(["start"]);
    expect(core.interactions[0].interaction.el).toBe(queryOne(".test:has(.inner)"));
});

test("recover from error as much as possible when applying dynamiccontent", async () => {
    let a = "a";
    let b = "b";
    let c = "c";
    let interaction = null;

    class Test extends Interaction {
        static selector = ".test";
        dynamicContent = {
            _root: {
                "t-att-a": () => a,
                "t-att-b": () => {
                    if (b === "boom") {
                        throw new Error("boom");
                    }
                    return b;
                },
                "t-att-c": () => c,
            },
        };
        setup() {
            interaction = this;
        }
    }

    await startInteraction(Test, `<div class="test"></div>`);
    expect(".test").toHaveOuterHTML(`<div class="test" a="a" b="b" c="c"></div>`);

    a = "aa";
    b = "boom";
    c = "cc";
    expect(() => interaction.updateContent()).toThrow(
        "An error occured while updating dynamic attribute 'b' (in interaction 'Test')"
    );
    expect(".test").toHaveOuterHTML(`<div class="test" a="aa" b="b" c="cc"></div>`);
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

    const { core } = await startInteraction(
        Test,
        `<div class="test"></div><div class="test"></div>`
    );
    expect.verifySteps(["setup 1", "setup 2"]);
    core.stopInteractions();
    expect.verifySteps(["destroy 2", "destroy 1"]);
});

test("can mount a component", async () => {
    class Test extends Component {
        static selector = ".test";
        static template = xml`owl component`;
        static props = {};
    }
    const { core } = await startInteraction(Test, `<div class="test"></div>`);
    expect(".test").toHaveInnerHTML(
        `<owl-component contenteditable="false" data-oe-protected="true">owl component</owl-component>`
    );
    core.stopInteractions();
    expect(".test").toHaveOuterHTML(`<div class="test"></div>`);
});

test("can start interaction in specific el", async () => {
    let n = 0;
    class Test extends Interaction {
        static selector = ".test";
        dynamicContent = {
            _root: { "t-att-a": () => "b" },
        };

        setup() {
            n++;
        }
    }

    const { core } = await startInteraction(Test, `<p></p>`);

    expect(n).toBe(0);
    const p = queryOne("p");
    p.innerHTML = `<div class="test">hello</div>`;
    core.startInteractions(queryOne(".test"));
    await animationFrame();
    expect(n).toBe(1);
    expect(p).toHaveInnerHTML(`<div class="test" a="b">hello</div>`);
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

    const { core } = await startInteraction(
        Test,
        `
        <p>
            <span class="a test"></span>
            <span class="b"></span>
        </p>`
    );

    expect(n).toBe(1);
    const p = queryOne("p");
    expect(p).toHaveInnerHTML(
        `<span class="a test" data-start="true"></span> <span class="b"></span>`
    );
    const b = queryOne("p .b");
    b.classList.add("test");
    await core.startInteractions(b);
    expect(n).toBe(2);
    expect(p).toHaveInnerHTML(
        `<span class="a test" data-start="true"></span> <span class="b test" data-start="true"></span>`
    );

    core.stopInteractions(b);
    expect(n).toBe(1);
    expect(p).toHaveInnerHTML(
        `<span class="a test" data-start="true"></span> <span class="b test"></span>`
    );
});

test("does not start interaction in el if not attached", async () => {
    let n = 0;
    class Test extends Interaction {
        static selector = ".test";
        start() {
            n++;
        }
        destroy() {
            n--;
        }
    }

    const { core } = await startInteraction(Test, `<p><span class="test"></span></p>`);
    expect(n).toBe(1);
    const span = queryOne("span.test");
    core.stopInteractions(span);
    expect(n).toBe(0);
    span.remove();
    await core.startInteractions(span);
    expect(n).toBe(0);
});
