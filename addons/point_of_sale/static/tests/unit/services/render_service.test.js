import { Deferred, expect, getFixture, microTick, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { advanceTime, mockFetch } from "@odoo/hoot-mock";
import { Component, onWillStart, xml } from "@odoo/owl";
import { htmlToCanvas } from "@point_of_sale/app/services/render_service";
import { allowTranslations, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { definePosModels } from "../data/generate_model_definitions.js";

definePosModels();
odoo.pos_session_id = 1;

test("test the render service", async () => {
    class ComponentToBeRendered extends Component {
        static props = ["name"];
        static template = xml`
            <div> It's me, <t t-esc="props.name" />! </div>
        `;
    }

    allowTranslations();
    const comp = await mountWithCleanup("none");
    const renderedComp = await comp.env.services.renderer.toHtml(
        ComponentToBeRendered,
        {
            name: "Mario",
        },
    );
    expect(renderedComp).toHaveOuterHTML("<div> It's me, Mario! </div>");
});

test("htmlToCanvas", async () => {
    mockFetch(() => "");
    const target = getFixture();
    const container = document.createElement("div");
    container.classList.add("render-container");
    target.appendChild(container);
    const node = document.createElement("div");
    node.classList.add("receipt");

    const asciiChars = Array.from({ length: 256 }, (_, i) =>
        String.fromCharCode(i),
    ).join("");
    node.textContent = asciiChars;

    let canvas = null;
    try {
        canvas = await htmlToCanvas(node, { addClass: "pos-receipt-print" });
    } catch (error) {
        if (error.constructor.name !== "Event") {
            throw error;
        }
    }
    expect(canvas).not.toBe(null, {
        message: "htmlToCanvas should work with all ascii characters",
    });
    expect(node.textContent).toBe(asciiChars);
    expect(node.className).toBe("receipt");
});

test("mounting a second receipt waits for the active callback", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    const renderer = comp.env.services.renderer;
    const container = document.createElement("div");
    getFixture().appendChild(container);
    const done = new Deferred();
    const first = renderer.whenMounted({
        el: document.createElement("div"),
        container,
        callback: async (clone) => {
            expect.step("first mounted");
            await done;
            expect(clone.isConnected).toBe(true);
            expect.step("first finished");
        },
    });
    await microTick();
    const second = renderer.whenMounted({
        el: document.createElement("span"),
        container,
        callback: () => expect.step("second mounted"),
    });
    await microTick();
    expect.verifySteps(["first mounted"]);
    done.resolve();
    await Promise.all([first, second]);
    expect.verifySteps(["first finished", "second mounted"]);
    expect(container.children).toHaveLength(1);
});

test("htmlToCanvas accepts a classless receipt without options", async () => {
    mockFetch(() => "");
    const container = document.createElement("div");
    container.className = "render-container";
    getFixture().appendChild(container);
    const node = document.createElement("div");
    node.textContent = "Receipt";
    const canvas = await htmlToCanvas(node);
    expect(canvas.width).toBeGreaterThan(0);
    expect(node.className).toBe("");
});

for (const className of ["", "receipt:w-80"]) {
    test(`whenMounted accepts receipt class ${JSON.stringify(className)}`, async () => {
        allowTranslations();
        const comp = await mountWithCleanup("none");
        const node = document.createElement("div");
        node.className = className;
        node.textContent = "Receipt";
        const container = document.createElement("div");
        getFixture().appendChild(container);
        await comp.env.services.renderer.whenMounted({
            el: node,
            container,
            callback: (clone) => {
                expect(clone.isConnected).toBe(true);
                expect(clone).not.toBe(node);
                expect(clone.textContent).toBe("Receipt");
            },
        });
    });
}

test("queued renders of the same component produce distinct receipts", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    class Receipt extends Component {
        static props = ["number"];
        static template = xml`<div t-esc="props.number"/>`;
    }
    const receipts = await Promise.all([
        comp.env.services.renderer.toHtml(Receipt, { number: "first" }),
        comp.env.services.renderer.toHtml(Receipt, { number: "second" }),
        comp.env.services.renderer.toHtml(Receipt, { number: "third" }),
    ]);
    expect(receipts.map((el) => el.textContent)).toEqual(["first", "second", "third"]);
    expect(new Set(receipts).size).toBe(3);
});

test("a timed-out component cannot resolve the next render", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    const ready = new Deferred();
    class SlowReceipt extends Component {
        static props = {};
        static template = xml`<div>slow</div>`;
        setup() {
            onWillStart(() => ready);
        }
    }
    class Receipt extends Component {
        static props = {};
        static template = xml`<div>next</div>`;
    }
    const slow = comp.env.services.renderer
        .toHtml(SlowReceipt, {})
        .catch((error) => error);
    await animationFrame();
    await advanceTime(10001);
    expect((await slow).message).toBe(
        "Component 'SlowReceipt' could not be rendered to HTML",
    );
    const next = comp.env.services.renderer.toHtml(Receipt, {});
    ready.resolve();
    expect((await next).textContent).toBe("next");
});

test("a failed mounted callback releases the container for the next job", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    const container = document.createElement("div");
    getFixture().appendChild(container);
    const renderer = comp.env.services.renderer;
    await expect(
        renderer.whenMounted({
            el: document.createElement("div"),
            container,
            callback: () => {
                throw new Error("Print failed");
            },
        }),
    ).rejects.toThrow("Print failed");
    expect(
        await renderer.whenMounted({
            el: document.createElement("span"),
            container,
            callback: (el) => el.tagName,
        }),
    ).toBe("SPAN");
});

test("mounted callbacks can render a component without replacing their own DOM", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    class Receipt extends Component {
        static props = {};
        static template = xml`<div>receipt</div>`;
    }
    const renderer = comp.env.services.renderer;
    await renderer.whenMounted({
        el: document.createElement("section"),
        callback: async (clone) => {
            expect((await renderer.toHtml(Receipt, {})).textContent).toBe("receipt");
            expect(clone.isConnected).toBe(true);
        },
    });
});

test("concurrent canvas conversions retain their own dimensions and source DOM", async () => {
    mockFetch(() => "");
    const container = document.createElement("div");
    container.className = "render-container";
    getFixture().appendChild(container);
    const nodes = [
        [48, 32],
        [96, 64],
    ].map(([width, height]) => {
        const node = document.createElement("div");
        node.style.cssText = `width:${width}px;height:${height}px`;
        node.textContent = `${width}`;
        return node;
    });
    const canvases = await Promise.all(
        nodes.map((node) => htmlToCanvas(node, { addClass: "receipt" })),
    );
    expect(canvases.map((canvas) => [canvas.width, canvas.height])).toEqual([
        [48, 32],
        [96, 64],
    ]);
    expect(nodes.map((node) => node.className)).toEqual(["", ""]);
    expect(nodes.map((node) => node.isConnected)).toEqual([false, false]);
});
