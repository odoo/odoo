// @ts-check

import { expect, getFixture, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, onWillDestroy, useSubEnv, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { OVERLAY_SYMBOL } from "@web/ui/overlay/overlay_container";

test("simple case", async () => {
    await mountWithCleanup(MainComponentsContainer);
    expect(".o-overlay-container").toHaveCount(1);

    class MyComp extends Component {
        static template = xml`
            <div class="overlayed"></div>
        `;
        static props = ["*"];
    }

    const remove = getService("overlay").add(MyComp, {});
    await animationFrame();
    expect(".o-overlay-container .overlayed").toHaveCount(1);

    remove();
    await animationFrame();
    expect(".o-overlay-container .overlayed").toHaveCount(0);
});

test("shadow DOM overlays are visible when registered before main component is mounted", async () => {
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed"></div>
        `;
        static props = ["*"];
    }

    const root = document.createElement("div");
    root.setAttribute("id", "my-root-id");
    root.attachShadow({ mode: "open" });
    getFixture().appendChild(root);

    await makeMockEnv();
    getService("overlay").add(MyComp, {}, { rootId: "my-root-id" });

    await mountWithCleanup(MainComponentsContainer, { target: root.shadowRoot });
    await animationFrame();

    expect("#my-root-id:shadow .o-overlay-container .overlayed").toHaveCount(1);
});

test("onRemove callback", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml``;
        static props = ["*"];
    }

    const onRemove = () => expect.step("onRemove");
    const remove = getService("overlay").add(MyComp, {}, { onRemove });

    expect.verifySteps([]);
    remove();
    expect.verifySteps(["onRemove"]);
});

test("double remove runs onRemove once (idempotent)", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml``;
        static props = ["*"];
    }

    /** @type {(value?: unknown) => void} */
    let resolveRemove;
    const onRemove = () => {
        expect.step("onRemove");
        return new Promise((resolve) => {
            resolveRemove = resolve;
        });
    };
    const remove = getService("overlay").add(MyComp, {}, { onRemove });

    remove();
    remove();
    expect.verifySteps(["onRemove"]);

    resolveRemove();
    await animationFrame();

    remove();
    expect.verifySteps([]);
});

test("a second close joins the removal already in flight", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`<div class="joined"/>`;
        static props = ["*"];
    }

    /** @type {() => void} */
    let release = () => {};
    const remove = getService("overlay").add(
        MyComp,
        {},
        {
            onRemove: () =>
                new Promise((resolve) => (release = () => resolve(undefined))),
        },
    );
    await animationFrame();
    expect(".joined").toHaveCount(1);

    remove();
    let settled = false;
    Promise.resolve(remove()).then(() => (settled = true));
    await animationFrame();
    expect(settled).toBe(false);

    release();
    await animationFrame();
    expect(settled).toBe(true);
    expect(".joined").toHaveCount(0);
});

test("joining a pending removal with removeParams warns in debug", async () => {
    patchWithCleanup(odoo, { debug: "1" });
    patchWithCleanup(console, {
        warn: (message) => expect.step(message),
    });
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml``;
        static props = ["*"];
    }

    /** @type {() => void} */
    let release = () => {};
    const remove = getService("overlay").add(
        MyComp,
        {},
        {
            onRemove: () =>
                new Promise((resolve) => (release = () => resolve(undefined))),
        },
    );
    await animationFrame();

    remove({ kept: true });
    remove();
    expect.verifySteps([], {
        message: "joining without params is the ordinary double close: silent",
    });
    remove({ dropped: true });
    expect.verifySteps([
        `[overlay] closing overlay 1 again while its removal is in flight: ` +
            `the provided removeParams are ignored.`,
    ]);

    release();
    await animationFrame();
});

test("multiple overlays", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed" t-att-class="props.className"></div>
        `;
        static props = ["*"];
    }

    const remove1 = getService("overlay").add(MyComp, { className: "o1" });
    const remove2 = getService("overlay").add(MyComp, { className: "o2" });
    const remove3 = getService("overlay").add(MyComp, { className: "o3" });
    await animationFrame();
    expect(".overlayed").toHaveCount(3);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o1");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o2");
    expect(".o-overlay-container :nth-child(3) .overlayed").toHaveClass("o3");

    remove1();
    await animationFrame();
    expect(".overlayed").toHaveCount(2);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o2");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o3");

    remove2();
    await animationFrame();
    expect(".overlayed").toHaveCount(1);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");

    remove3();
    await animationFrame();
    expect(".overlayed").toHaveCount(0);
});

test("sequence", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed" t-att-class="props.className"></div>
        `;
        static props = ["*"];
    }

    const remove1 = getService("overlay").add(
        MyComp,
        { className: "o1" },
        { sequence: 50 },
    );
    const remove2 = getService("overlay").add(
        MyComp,
        { className: "o2" },
        { sequence: 60 },
    );
    const remove3 = getService("overlay").add(
        MyComp,
        { className: "o3" },
        { sequence: 40 },
    );
    await animationFrame();
    expect(".overlayed").toHaveCount(3);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o1");
    expect(".o-overlay-container :nth-child(3) .overlayed").toHaveClass("o2");

    remove1();
    await animationFrame();
    expect(".overlayed").toHaveCount(2);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o2");

    remove2();
    await animationFrame();
    expect(".overlayed").toHaveCount(1);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");

    remove3();
    await animationFrame();
    expect(".overlayed").toHaveCount(0);
});

test("allow env as option", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static props = ["*"];
        static template = xml`
            <ul class="outer">
                <li>A=<t t-out="env.A"/></li>
                <li>B=<t t-out="env.B"/></li>
            </ul>
        `;
        setup() {
            useSubEnv({ A: "blip" });
        }
    }

    getService("overlay").add(MyComp, {}, { env: { A: "foo", B: "bar" } });
    await animationFrame();

    expect(".o-overlay-container li:nth-child(1)").toHaveText("A=blip");
    expect(".o-overlay-container li:nth-child(2)").toHaveText("B=bar");
});

async function mountShadowOverlayContainer(hostId, parent) {
    const { OverlayContainer } = await import("@web/ui/overlay/overlay_container");
    const { App } = await import("@odoo/owl");
    const { getTemplate } = await import("@web/core/templates");
    const host = document.createElement("div");
    host.id = hostId;
    parent.appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    const overlays = getService("overlay").overlays;
    class ShadowHost extends Component {
        static components = { OverlayContainer };
        static props = {};
        static template = xml`<OverlayContainer overlays="overlays" rootId="rootId"/>`;
        setup() {
            this.overlays = overlays;
            this.rootId = hostId;
        }
    }
    const app = new App(ShadowHost, { getTemplate, test: true });
    await app.mount(shadow);
    return { app, shadow };
}

test("click in a shadow-root overlay closes a main-document popover", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const target = getFixture();
    class Content extends Component {
        static template = xml`<div class="pop-content">popover</div>`;
        static props = ["*"];
    }
    class Foreign extends Component {
        static template = xml`<button class="foreign-content">foreign</button>`;
        static props = ["*"];
    }

    const { app, shadow } = await mountShadowOverlayContainer("otherRoot", target);

    getService("popover").add(target, Content);
    getService("overlay").add(Foreign, {}, { rootId: "otherRoot" });
    await animationFrame();

    expect(".pop-content").toHaveCount(1);
    const foreignEl = shadow.querySelector(".foreign-content");
    expect(Boolean(foreignEl)).toBe(true);

    await click(foreignEl);
    await animationFrame();
    expect(".pop-content").toHaveCount(0);
    app.destroy();
});

test("mounting a second container does not transiently mount foreign overlays", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const target = getFixture();
    const steps = [];
    class Tracked extends Component {
        static template = xml`<div class="tracked">tracked</div>`;
        static props = ["*"];
        setup() {
            onMounted(() => {
                steps.push("mounted");
            });
            onWillDestroy(() => {
                steps.push("destroyed");
            });
        }
    }
    getService("overlay").add(Tracked, {});
    await animationFrame();
    expect(steps).toEqual(["mounted"]);

    const { app } = await mountShadowOverlayContainer("secondRoot", target);
    await animationFrame();

    expect(steps).toEqual(["mounted"]);
    app.destroy();
});

test("destroy() does not leak an unhandled rejection from onRemove", async () => {
    const env = await makeMockEnv();
    class Boom extends Component {
        static props = ["*"];
        static template = xml`<div class="boom"/>`;
    }
    env.services.overlay.add(
        Boom,
        {},
        { onRemove: () => Promise.reject(new Error("onClose blew up")) },
    );

    let unhandled = null;
    const onUnhandled = (ev) => {
        unhandled = ev.reason?.message ?? String(ev.reason);
        ev.preventDefault();
    };
    window.addEventListener("unhandledrejection", onUnhandled);
    try {
        env.services.overlay.destroy();
        await new Promise((resolve) => setTimeout(resolve, 50));
    } finally {
        window.removeEventListener("unhandledrejection", onUnhandled);
    }
    expect(unhandled).toBe(null);
});

test("click-away containment spans sub-overlays without allocating per sibling", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class Layer extends Component {
        static props = ["*"];
        static template = xml`<div t-att-class="props.name"/>`;
    }
    const overlay = getService("overlay");
    overlay.add(Layer, { name: "low" }, { sequence: 10 });
    overlay.add(Layer, { name: "high" }, { sequence: 90 });
    await animationFrame();

    const low = document.querySelector(".low");
    const high = document.querySelector(".high");
    expect(low).not.toBe(null);
    expect(high).not.toBe(null);

    const items = [...document.querySelectorAll(".o-overlay-item")];
    expect(items).toHaveLength(2);
    expect(items[0].contains(low)).toBe(true);
    expect(items[1].contains(high)).toBe(true);
    expect(items[1].contains(low)).toBe(false);
});

test("a hosted env REPLACES the container's env instead of extending it", async () => {
    await mountWithCleanup(MainComponentsContainer);

    /** @type {{ hosted: string, inheritedServices: boolean, overlay: boolean }} */
    let seen;
    class Probe extends Component {
        static props = ["*"];
        static template = xml`<div class="probe"/>`;
        setup() {
            seen = {
                hosted: this.env.HOSTED,
                inheritedServices: "services" in this.env,
                overlay: Boolean(this.env[OVERLAY_SYMBOL]),
            };
        }
    }

    getService("overlay").add(Probe, {}, { env: { HOSTED: "yes" } });
    await animationFrame();

    expect(seen.hosted).toBe("yes");
    expect(seen.inheritedServices).toBe(false);
    expect(seen.overlay).toBe(true);
});

test("a hosted overlay still reports containment to click-away", async () => {
    await mountWithCleanup(MainComponentsContainer);

    /** @type {(node: Node) => boolean} */
    let contains;
    class Probe extends Component {
        static props = ["*"];
        static template = xml`<div class="hosted-probe"/>`;
        setup() {
            contains = (/** @type {Node} */ node) =>
                this.env[OVERLAY_SYMBOL].contains(node);
        }
    }
    getService("overlay").add(Probe, {}, { env: { HOSTED: "yes" } });
    await animationFrame();

    expect(contains(document.querySelector(".hosted-probe"))).toBe(true);
    expect(contains(document.body)).toBe(false);
});

test("a throwing onRemove removes the overlay and hands the caller the error", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`<div class="overlayed"/>`;
        static props = ["*"];
    }
    const remove = getService("overlay").add(
        MyComp,
        {},
        {
            onRemove: () => {
                expect.step("onRemove");
                throw new Error("onClose blew up");
            },
        },
    );
    await animationFrame();
    expect(".overlayed").toHaveCount(1);

    await remove().catch((error) => expect.step(error.message));
    await animationFrame();

    expect(".overlayed").toHaveCount(0);
    expect.verifySteps(["onRemove", "onClose blew up"]);
});

test("unregistering a container twice preserves another registration for the same root", async () => {
    await makeMockEnv();
    const overlay = getService("overlay");
    const first = overlay.registerContainer("shared-root");
    const second = overlay.registerContainer("shared-root");
    first();
    first();
    expect([...overlay.containerRoots.values()]).toEqual(["shared-root"]);
    second();
    expect([...overlay.containerRoots.values()]).toEqual([]);
});

test("an old container disposer cannot unregister its replacement", async () => {
    await makeMockEnv();
    const overlay = getService("overlay");
    const old = overlay.registerContainer("replacement-root");
    old();
    const replacement = overlay.registerContainer("replacement-root");
    old();
    expect([...overlay.containerRoots.values()]).toEqual(["replacement-root"]);
    replacement();
    expect([...overlay.containerRoots.values()]).toEqual([]);
});

test("unregistering a later duplicate root preserves the first fallback owner's order", async () => {
    await makeMockEnv();
    const overlay = getService("overlay");
    const first = overlay.registerContainer("first");
    const middle = overlay.registerContainer("middle");
    const last = overlay.registerContainer("first");
    last();
    expect([...overlay.containerRoots.values()]).toEqual(["first", "middle"]);
    first();
    expect([...overlay.containerRoots.values()]).toEqual(["middle"]);
    middle();
});
