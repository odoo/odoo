// @ts-check

import { destroy, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { makePopover, usePopover } from "@web/ui/popover/popover_hook";

class ChallengeContent extends Component {
    static template = xml`<div t-att-data-name="props.name">content</div>`;
    static props = ["*"];
}

test("a failed add does not leave the hook claiming an open popover", () => {
    const popover = makePopover(
        () => {
            throw new Error("add failed");
        },
        ChallengeContent,
        {},
    );
    expect(() => popover.open(getFixture(), {})).toThrow("add failed");
    expect(popover.isOpen).toBe(false);
    expect(popover.close()).toBe(undefined);
});

test("an obsolete detached-target close cannot lose the replacement popover", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const popover = makePopover(
        (...args) => getService("popover").add(...args),
        ChallengeContent,
        {},
    );
    popover.open(document.createElement("button"), { name: "detached" });
    popover.open(getFixture(), { name: "connected" });
    await animationFrame();
    expect(".o_popover [data-name=connected]").toHaveCount(1);
    expect(popover.isOpen).toBe(true);
    await popover.close();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test("reopening from onClose does not orphan a popover", async () => {
    await mountWithCleanup(MainComponentsContainer);
    let calls = 0;
    const popover = makePopover(
        (...args) => getService("popover").add(...args),
        ChallengeContent,
        {
            onClose: () => {
                if (++calls === 1) {
                    popover.open(getFixture(), { name: "callback" });
                }
            },
        },
    );
    popover.open(getFixture(), { name: "first" });
    await animationFrame();
    popover.open(getFixture(), { name: "outer" });
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover [data-name=callback]").toHaveCount(1);
    await popover.close();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test("the hook propagates a rejected close and still removes its overlay", async () => {
    const done = new Deferred();
    class Owner extends Component {
        static template = xml`<button>target</button>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(ChallengeContent, { onClose: () => done });
        }
    }
    const owner = await mountWithCleanup(Owner);
    owner.popover.open(getFixture(), {});
    await animationFrame();
    const failure = new Error("close rejected");
    const outcome = owner.popover.close().then(
        () => "resolved",
        (error) => error,
    );
    done.reject(failure);
    expect(await outcome).toBe(failure);
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test("closing through the hook waits for the owner's async callback", async () => {
    const done = new Deferred();
    class Content extends Component {
        static template = xml`<div>content</div>`;
        static props = ["*"];
    }
    class Owner extends Component {
        static template = xml`<button>target</button>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(Content, {
                onClose: () => done,
            });
        }
    }
    const owner = await mountWithCleanup(Owner);
    owner.popover.open(getFixture(), {});
    await animationFrame();
    let closed = false;
    const closing = owner.popover.close().then(() => {
        closed = true;
    });
    await animationFrame();
    expect(closed).toBe(false);
    done.resolve();
    await closing;
    expect(closed).toBe(true);
});

test("close popover when component is unmounted", async () => {
    const target = getFixture();
    class Comp extends Component {
        static template = xml`<div t-att-id="props.id">in popover</div>`;
        static props = ["*"];
    }

    class CompWithPopover extends Component {
        static template = xml`<div />`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(Comp);
        }
    }

    const comp1 = await mountWithCleanup(CompWithPopover);
    comp1.popover.open(target, { id: "comp1" });
    await animationFrame();

    const comp2 = await mountWithCleanup(CompWithPopover, { noMainContainer: true });
    comp2.popover.open(target, { id: "comp2" });
    await animationFrame();

    expect(".o_popover").toHaveCount(2);
    expect(".o_popover #comp1").toHaveCount(1);
    expect(".o_popover #comp2").toHaveCount(1);

    destroy(comp1);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp1").toHaveCount(0);
    expect(".o_popover #comp2").toHaveCount(1);

    destroy(comp2);
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp1").toHaveCount(0);
    expect(".o_popover #comp2").toHaveCount(0);
});

test("popover opened from another", async () => {
    class Comp extends Component {
        static id = 0;
        static template = xml`
            <div class="p-4">
                <button class="pop-open" t-on-click="(ev) => this.popover.open(ev.target, {})">open popover</button>
            </div>
        `;
        static props = ["*"];
        setup() {
            this.popover = usePopover(Comp, {
                class: `popover-${++Comp.id}`,
            });
        }
    }

    await mountWithCleanup(Comp);

    await contains(".pop-open").click();
    expect(".popover-1").toHaveCount(1);

    await contains(".popover-1 .pop-open").click();
    expect(".o_popover").toHaveCount(2);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);

    await contains(".popover-2 .pop-open").click();
    expect(".o_popover").toHaveCount(3);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);
    expect(".popover-3").toHaveCount(1);

    await contains(".popover-3").click();
    expect(".o_popover").toHaveCount(3);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);
    expect(".popover-3").toHaveCount(1);

    await contains(".popover-2").click();
    expect(".o_popover").toHaveCount(2);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);

    await contains(document.body).click();
    expect(".o_popover").toHaveCount(0);
});

test("a hosted component's close reason reaches onClose", async () => {
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string | {reason: string}} */
    let received;
    class Closer extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
        setup() {
            this.props.close({ reason: "picked" });
        }
    }

    const popover = makePopover(
        (...args) => getService("popover").add(...args),
        Closer,
        {
            onClose: (params) => (received = params),
        },
    );
    popover.open(getFixture(), {});
    await animationFrame();
    await animationFrame();
    expect(received).toEqual({ reason: "picked" });
});

test("the owner's own close reason reaches onClose", async () => {
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string | {reason: string}} */
    let received;
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    const popover = makePopover((...args) => getService("popover").add(...args), Comp, {
        onClose: (params) => (received = params),
    });
    popover.open(getFixture(), {});
    await animationFrame();
    popover.close({ reason: "owner" });
    await animationFrame();
    await animationFrame();
    expect(received).toEqual({ reason: "owner" });
});

test("an unknown option still warns through the hook's option bag", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    const warnings = [];
    patchWithCleanup(console, {
        warn: (...args) => warnings.push(args.join(" ")),
    });
    patchWithCleanup(odoo, { debug: "1" });

    const popover = makePopover((...args) => getService("popover").add(...args), Comp, {
        // @ts-expect-error
        totallyBogusOption: true,
    });
    popover.open(getFixture(), {});
    await animationFrame();

    expect(warnings.filter((w) => w.includes("totallyBogusOption"))).toHaveLength(1);
});
