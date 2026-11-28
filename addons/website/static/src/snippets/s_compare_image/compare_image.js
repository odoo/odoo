import { registry } from "@web/core/registry";
import { clamp } from "@web/core/utils/numbers";
import { Interaction } from "@web/public/interaction";

export class CompareImage extends Interaction {
    static selector = ".s_compare_image";

    dynamicContent = {
        _root: {
            "t-att-style": () => ({ "--s_compare_image-position": `${this.position}%` }),
        },
        ".s_compare_image_divider": {
            "t-on-pointerdown": this.onPointerDown,
            "t-on-pointermove": this.onPointerMove,
            "t-on-pointerup": () => {
                this.isDragging = false;
            },
        },
    };

    setup() {
        this.position = parseFloat(
            getComputedStyle(this.el).getPropertyValue("--s_compare_image-position")
        );
        this.isDragging = false;
        this.frameEl = this.el.querySelector(".s_compare_image_frame");
        this.isHorizontal = this.el.classList.contains("s_compare_image_horizontal");
        // In RTL the vertical divider is placed from the right edge.
        this.isMirrored = !this.isHorizontal && !!this.el.closest(".o_rtl, [dir='rtl']");
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
        this.isDragging = true;
        // Keeps the gap between the pointer and the divider, so grabbing the
        // handle off-centre does not make the divider jump to the pointer.
        this.offset = this.getPointerPosition(ev) - this.position;
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerMove(ev) {
        if (!this.isDragging) {
            return;
        }

        this.position = clamp(this.getPointerPosition(ev) - this.offset, 0, 100);
    }

    /**
     * @param {PointerEvent} ev
     * @returns {number} the pointer's place in the frame, in percent
     */
    getPointerPosition(ev) {
        const { left, top, width, height } = this.frameEl.getBoundingClientRect();
        const ratio = this.isHorizontal ? (ev.clientY - top) / height : (ev.clientX - left) / width;
        return (this.isMirrored ? 1 - ratio : ratio) * 100;
    }
}

registry.category("public.interactions").add("website.compare_image", CompareImage);
