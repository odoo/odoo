import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { clamp } from "@web/core/utils/numbers";

export class CompareImage extends Interaction {
    static selector = ".s_compare_image";
    static selectorHas = ".s_compare_image_divider";

    dynamicContent = {
        _root: {
            "t-att-style": () => ({ "--compare-pos": `${this.position}%` }),
        },
        ".s_compare_image_divider": {
            "t-on-pointerdown": this.onPointerDown,
            "t-on-pointermove": this.throttled(this.onPointerMove),
            "t-on-pointerup": this.stopDragging,
        },
    };

    setup() {
        const position = parseFloat(getComputedStyle(this.el).getPropertyValue("--compare-pos"));

        this.position = Number.isFinite(position) ? position : 50;
        this.isDragging = false;
        this.frameEl = this.el.querySelector(".s_compare_image_frame");
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerDown(ev) {
        if (ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        ev.currentTarget.setPointerCapture(ev.pointerId);

        const rect = this.frameEl.getBoundingClientRect();
        this.isHorizontal = this.el.classList.contains("s_compare_image_horizontal");
        // In RTL the vertical divider is placed from the right edge, so moving
        // the pointer right lowers its position.
        this.isMirrored = !this.isHorizontal && !!this.el.closest(".o_rtl, [dir='rtl']");
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
        this.position = clamp(this.startPosition + (this.isMirrored ? -delta : delta), 0, 100);
    }

    /**
     * @param {PointerEvent} ev
     */
    stopDragging(ev) {
        if (!this.isDragging) {
            return;
        }
        // Applies the final pointer position synchronously: the throttled move
        // handler may still have a frame pending, which it drops once
        // `isDragging` is reset.
        this.onPointerMove(ev);
        this.isDragging = false;
    }
}

registry.category("public.interactions").add("website.compare_image", CompareImage);
