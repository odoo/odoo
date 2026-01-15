import { test, describe, expect } from "@odoo/hoot";
import { useDraggableScroll } from "@pos_self_order/app/utils/scroll_dnd_hook";
import { Component, useRef, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

const setupComponent = async () => {
    await setupSelfPosEnv();
    class TestComponent extends Component {
        static template = xml`<div style="width: 200px; overflow-x: auto;" t-ref="scroll">
            <div style="width: 1000px; height: 20px;">Scrollable Content</div>
        </div>`;
        static props = [];
        setup() {
            this.scrollRef = useRef("scroll");
            useDraggableScroll(this.scrollRef);
        }
    }

    const comp = await mountWithCleanup(TestComponent, {});
    const scrollEl = comp.scrollRef.el;
    const dispatchEvent = (type, clientX, opts) => {
        scrollEl.dispatchEvent(
            new MouseEvent(type, {
                bubbles: true,
                clientX: clientX,
                ...opts,
            })
        );
    };
    return { comp, scrollEl, dispatchEvent };
};

describe("useDraggableScroll", () => {
    test.tags("desktop");
    test("drags and scrolls horizontally", async () => {
        const { scrollEl, dispatchEvent } = await setupComponent();
        // Simulate mouse drag
        dispatchEvent("mousedown", 800);
        dispatchEvent("mousemove", 500); // drag left
        dispatchEvent("mouseup");
        expect(scrollEl.scrollLeft).toBeGreaterThan(0);
    });

    test.tags("desktop");
    test("does not scroll if movement is less than threshold", async () => {
        const { scrollEl, dispatchEvent } = await setupComponent();

        dispatchEvent("mousedown", 500);
        dispatchEvent("mousemove", 500 + 2); // small move
        dispatchEvent("mouseup");
        expect(scrollEl.scrollLeft).toBe(0);
    });
});
