// @ts-check

import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";
import { Popover } from "@web/ui/popover/popover";

class Carrier {
    constructor() {
        this.secret = 42;
    }
    getSecret() {
        return this.secret;
    }
}

test("presenter option validation follows a prop schema patched after first use", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const target = document.createElement("button");
    getFixture().append(target);
    const service = getService("popover");
    const close = service.add(
        target,
        probeComponent(() => {}),
    );
    await close();
    const warnings = [];
    patchWithCleanup(console, { warn: (message) => warnings.push(message) });
    patchWithCleanup(Popover.props, {
        patchedOption: { type: String, optional: true },
    });
    const remove = service.add(
        target,
        probeComponent(() => {}),
        {},
        // This test extends the runtime schema beyond the static option type.
        /** @type {any} */ ({ patchedOption: "value" }),
    );
    await remove();
    expect(warnings).toEqual([]);
});

/**
 * @param {(props: any) => void} onSetup
 * @returns {typeof Component}
 */
function probeComponent(onSetup) {
    return /** @type {any} */ (
        class Probe extends Component {
            static template = xml`<div class="probed"/>`;
            static props = ["*"];
            setup() {
                onSetup(this.props);
            }
        }
    );
}

test("overlay.add hands the hosted component the props it was given, not a proxy", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const carrier = new Carrier();
    const byIdentity = new Map([[carrier, "found"]]);
    /** @type {any} */
    let seen;
    getService("overlay").add(
        probeComponent((props) => (seen = props.value)),
        { value: carrier },
    );
    await animationFrame();

    expect(seen).toBe(carrier);
    expect(byIdentity.get(seen)).toBe("found");
    expect(new Set([carrier]).has(seen)).toBe(true);
    expect(seen.getSecret()).toBe(42);
});

test("overlay.add leaves nested values alone too", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const carrier = new Carrier();
    /** @type {any} */
    let seen;
    getService("overlay").add(
        probeComponent((props) => (seen = props.items)),
        { items: [carrier] },
    );
    await animationFrame();

    expect(seen[0]).toBe(carrier);
});

test("the presenters share one option contract, and still name real typos", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string[]} */
    const warnings = [];
    patchWithCleanup(console, {
        warn: (/** @type {string} */ message) => warnings.push(message),
    });

    const target = document.createElement("div");
    /** @type {HTMLElement} */ (getFixture()).appendChild(target);
    getService("popover").add(
        target,
        probeComponent(() => {}),
        {},
        /** @type {any} */ ({
            position: "top",
            onBack: () => {},
            nonsense: 1,
        }),
    );
    await animationFrame();

    expect(warnings.filter((w) => w.includes("onBack"))).toHaveLength(0);
    expect(warnings.filter((w) => w.includes("position"))).toHaveLength(0);
    expect(warnings.filter((w) => w.includes("nonsense"))).toHaveLength(1);
});

test("a dropdown rendered as a bottom sheet reports nothing about its popover options", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string[]} */
    const warnings = [];
    patchWithCleanup(console, {
        warn: (/** @type {string} */ message) => warnings.push(message),
    });

    const target = document.createElement("div");
    /** @type {HTMLElement} */ (getFixture()).appendChild(target);
    getService("bottom_sheet").add(
        target,
        probeComponent(() => {}),
        {},
        /** @type {any} */ ({
            animation: false,
            arrow: false,
            holdOnHover: false,
            onPositioned: () => {},
            position: "bottom",
        }),
    );
    await animationFrame();

    expect(warnings).toHaveLength(0);
});

test("dialog.add names the options it will not act on, debug or not", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string[]} */
    const warnings = [];
    patchWithCleanup(console, {
        warn: (/** @type {string} */ message) => warnings.push(message),
    });

    getService("dialog").add(
        probeComponent(() => {}),
        {},
        /** @type {any} */ ({
            sequence: 10,
            closeOnEscape: false,
            context: {},
        }),
    );
    await animationFrame();

    expect(warnings.filter((w) => w.includes("closeOnEscape"))).toHaveLength(1);
    expect(warnings.filter((w) => w.includes("context"))).toHaveLength(1);
    expect(warnings.filter((w) => w.includes("sequence"))).toHaveLength(0);
});

test("dialog.add honours sequence", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class First extends Component {
        static template = xml`<div class="first"/>`;
        static props = ["*"];
    }
    class Second extends Component {
        static template = xml`<div class="second"/>`;
        static props = ["*"];
    }
    getService("dialog").add(First, {}, { sequence: 90 });
    getService("dialog").add(Second, {}, { sequence: 10 });
    await animationFrame();

    const order = [...document.querySelectorAll(".first, .second")].map(
        (el) => el.className,
    );
    expect(order).toEqual(["second", "first"]);
});

test("OverlayContainer names the service it could not find", async () => {
    await makeMockEnv();
    let message = "";
    try {
        await mountWithCleanup(OverlayContainer, {
            env: /** @type {any} */ ({ services: {} }),
        });
    } catch (error) {
        message = String(/** @type {any} */ (error).cause?.message ?? error);
    }
    expect(message).toInclude("overlay");
    expect(message).toInclude("OverlayContainer");
});

test("a throwing onRemove still tears the overlay down", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const remove = getService("overlay").add(
        probeComponent(() => {}),
        {},
        {
            onRemove: () => {
                throw new Error("onClose exploded");
            },
        },
    );
    await animationFrame();
    expect(".probed").toHaveCount(1);

    await expect(remove()).rejects.toThrow("onClose exploded");
    await animationFrame();
    expect(".probed").toHaveCount(0);

    expect(Object.keys(getService("overlay").overlays)).toHaveLength(0);
});
