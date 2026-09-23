// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    enrich,
    useEnrichWithActionLinks,
} from "@web/webclient/actions/reports/report_hook";

/**
 * @param {import("@odoo/owl").Ref} ref
 * @returns {HTMLElement}
 */
function mountedEl(ref) {
    const el = ref.el;
    if (!el) {
        throw new Error("the ref holds no element");
    }
    return el;
}

class EnrichHost extends Component {
    static template = xml`
        <div t-ref="root">
            <span res-id="1" res-model="partner" view-type="form" class="tgt">x</span>
            <span res-id="2" res-model="partner" view-type="form" class="tgt">y</span>
            <span class="untouched">z</span>
        </div>`;
    static props = {};

    /** @type {import("@odoo/owl").Ref} */
    root;

    setup() {
        this.root = useRef("root");
        useEnrichWithActionLinks(this.root);
    }
}

describe.current.tags("desktop");

test("every matching element is wrapped in exactly one action anchor", async () => {
    await mountWithCleanup(EnrichHost);
    expect(".tgt").toHaveCount(2);
    expect("a > .tgt").toHaveCount(2);
    expect("a > a").toHaveCount(0);
    expect("a > .untouched").toHaveCount(0);
});

test("a wrapped element still matches the selector it was found by", async () => {
    const comp = await mountWithCleanup(EnrichHost);
    expect(
        mountedEl(comp.root).querySelectorAll("[res-id][res-model][view-type]"),
    ).toHaveLength(2);
});

test("re-running enrich on already-enriched DOM adds nothing", async () => {
    const comp = await mountWithCleanup(EnrichHost);
    const rootEl = mountedEl(comp.root);
    const anchorsAfterMount = rootEl.querySelectorAll("a").length;
    expect(anchorsAfterMount).toBe(2);

    enrich(comp, rootEl);
    enrich(comp, rootEl);

    expect(rootEl.querySelectorAll("a")).toHaveLength(anchorsAfterMount);
    expect("a > a").toHaveCount(0);
    expect("a > .tgt").toHaveCount(2);
});

test("enrich still wraps elements added after the first pass", async () => {
    const comp = await mountWithCleanup(EnrichHost);
    const rootEl = mountedEl(comp.root);
    const fresh = document.createElement("span");
    fresh.setAttribute("res-id", "3");
    fresh.setAttribute("res-model", "partner");
    fresh.setAttribute("view-type", "form");
    fresh.classList.add("tgt");
    rootEl.appendChild(fresh);

    enrich(comp, rootEl);

    expect("a > .tgt").toHaveCount(3);
    expect("a > a").toHaveCount(0);
});

class ConditionalEnrichHost extends Component {
    static template = xml`
        <div>
            <div t-if="this.state.shown" t-ref="root">
                <span res-id="1" res-model="partner" view-type="form" class="tgt">x</span>
            </div>
        </div>`;
    static props = {};

    /** @type {{ shown: boolean }} */
    state;
    /** @type {import("@odoo/owl").Ref} */
    root;

    setup() {
        this.state = useState({ shown: true });
        this.root = useRef("root");
        useEnrichWithActionLinks(this.root);
    }
}

test("a target removed from the DOM hands the hook a null ref, not a crash", async () => {
    const comp = await mountWithCleanup(ConditionalEnrichHost);
    expect("a > .tgt").toHaveCount(1);

    comp.state.shown = false;
    await animationFrame();

    expect(".tgt").toHaveCount(0);
});

class IframeEnrichHost extends Component {
    static template = xml`<iframe t-ref="frame" t-att-srcdoc="this.doc"/>`;
    static props = {};
    doc = `<body><span res-id="7" res-model="partner" view-type="form" class="tgt">x</span></body>`;

    /** @type {import("@odoo/owl").Ref} */
    frame;

    setup() {
        this.frame = useRef("frame");
        useEnrichWithActionLinks(this.frame);
    }
}

test("an iframe's document is enriched once it loads", async () => {
    const comp = await mountWithCleanup(IframeEnrichHost);
    let anchor = null;
    for (let i = 0; i < 50 && !anchor; i++) {
        anchor = /** @type {HTMLIFrameElement | null} */ (
            comp.frame.el
        )?.contentDocument?.body?.querySelector("a > .tgt");
        await animationFrame();
    }
    expect(!!anchor).toBe(true);
});
