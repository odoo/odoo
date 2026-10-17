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
            // Throttled for animation: the move handler reads the layout, so
            // it must run at most once per frame.
            "t-on-pointermove": this.throttled(this.onPointerMove),
            "t-on-pointerup": this.stopDragging,
            "t-on-pointercancel": this.stopDragging,
            "t-on-lostpointercapture": this.stopDragging,
        },
    };

    setup() {
        // The divider position lives in a single custom property, which the
        // snippet markup (and later the builder option) sets inline.
        const position = parseFloat(getComputedStyle(this.el).getPropertyValue("--compare-pos"));
        this.position = Number.isFinite(position) ? position : 50;
        this.isDragging = false;
        // The drag is measured against the image frame, not the root: the root
        // is a <figure> that also contains the caption, so its height would
        // make the horizontal variant's maths wrong.
        this.frameEl = this.el.querySelector(".s_compare_image_frame");
    }

    /**
     * Edit mode overrides this to an empty object: the editor ignores t-att-*
     * writes and restores them to their initial value when the interaction is
     * destroyed, so there the position is written as a real inline style.
     */
    get rootStyle() {
        return { "--compare-pos": `${this.position}%` };
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerDown(ev) {
        if (ev.button !== 0) {
            return;
        }
        // Prevents the native image drag and the text selection that would
        // otherwise start on the labels.
        ev.preventDefault();
        // Capturing keeps the move/up events coming once the pointer leaves the
        // divider, so no window-level listener is needed.
        ev.currentTarget.setPointerCapture(ev.pointerId);
        this.isDragging = true;
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerMove(ev) {
        if (!this.isDragging) {
            return;
        }
        const rect = this.frameEl.getBoundingClientRect();
        // Read live rather than cached: the orientation can be switched from
        // the builder while the interaction is running.
        const ratio = this.el.classList.contains("s_compare_image_horizontal")
            ? (ev.clientY - rect.top) / rect.height
            : (ev.clientX - rect.left) / rect.width;
        this.position = clamp(ratio * 100, 0, 100);
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
        // The pointer capture is released implicitly on pointerup.
        this.isDragging = false;
    }
}

registry.category("public.interactions").add("website.compare_image", CompareImage);
