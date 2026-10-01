import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { clamp } from "@web/core/utils/numbers";

export class CompareImage extends Interaction {
    static selector = ".s_compare_image";
    static selectorHas = ".s_compare_image_divider";

    dynamicContent = {
        _root: {
            "t-att-style": () => this.rootStyle,
        },
        ".s_compare_image_divider": {
            "t-on-pointerdown": this.onPointerDown,
            "t-on-pointermove": (ev) => this.isDragging && this.throttledMove(ev),
            "t-on-pointerup": this.stopDragging,
        },
    };

    setup() {
        // Throttled for animation: the handler is what drives the repaint, so
        // it must run at most once per frame however fast the pointer polls.
        this.throttledMove = this.throttled(this.onPointerMove);

        // The divider position lives in a single custom property, which the
        // snippet markup (and later the builder option) sets inline.
        const position = parseFloat(getComputedStyle(this.el).getPropertyValue("--compare-pos"));

        this.position = Number.isFinite(position) ? position : 50;
        this.isDragging = false;
        this.frameEl = this.el.querySelector(".s_compare_image_frame");
    }

    get rootStyle() {
        return { "--compare-pos": `${this.position}%` };
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerDown(ev) {
        // Prevents the native image drag and the text selection that would
        // otherwise start on the labels.
        ev.preventDefault();
        // Capturing keeps the move/up events coming once the pointer leaves the
        // divider, so no window-level listener is needed.
        ev.currentTarget.setPointerCapture(ev.pointerId);

        const rect = this.frameEl.getBoundingClientRect();
        this.isHorizontal = this.el.classList.contains("s_compare_image_horizontal");
        this.frameSize = this.isHorizontal ? rect.height : rect.width;
        this.startCoord = this.isHorizontal ? ev.clientY : ev.clientX;
        this.startPosition = this.position;
        this.isDragging = true;
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerMove(ev) {
        if (!this.isDragging) {
            return;
        }

        const coord = this.isHorizontal ? ev.clientY : ev.clientX;
        const delta = ((coord - this.startCoord) / this.frameSize) * 100;
        this.position = clamp(this.startPosition + delta, 0, 100);
    }

    /**
     * @param {PointerEvent} ev
     */
    stopDragging(ev) {
        if (!this.isDragging) {
            return;
        }
        // Applies the final pointer position synchronously: the throttled move
        // handler may still have a frame pending, which the guard below would
        // otherwise make it drop.
        this.onPointerMove(ev);
        this.isDragging = false;
    }
}

registry.category("public.interactions").add("website.compare_image", CompareImage);
