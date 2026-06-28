import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ClickableCard extends Interaction {
    static selector = ".s_card";
    static selectorHas = ":scope > a.stretched-link";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        // Only define the dynamicSelector when there is at least one hoverable
        // image, to only add the listeners when necessary
        _clickableEl: () => (this.hoverableImageEls.length ? this.el : undefined),
    };
    dynamicContent = {
        _clickableEl: {
            "t-on-mouseenter": this.handleImageHovering,
            "t-on-mousemove": this.handleImageHovering,
            "t-on-mouseleave": this.stopImageHovering,
        },
    };

    setup() {
        this.hoverableImageEls = [...this.el.querySelectorAll("img[data-hover-effect]")];
        this.hoveredImageEl = null;
    }

    stopImageHovering() {
        if (this.hoveredImageEl) {
            this.hoveredImageEl.dispatchEvent(new MouseEvent("mouseleave", { view: window }));
            this.hoveredImageEl = null;
        }
    }

    isImageHovered(imgEl, clientX, clientY) {
        const rect = imgEl.getBoundingClientRect();
        return (
            rect.left <= clientX &&
            clientX <= rect.right &&
            rect.top <= clientY &&
            clientY <= rect.bottom
        );
    }

    handleImageHovering(ev) {
        const { clientX, clientY } = ev;
        const nextHoveredImageEl = this.hoverableImageEls.find((imgEl) =>
            this.isImageHovered(imgEl, clientX, clientY)
        );

        if (this.hoveredImageEl === nextHoveredImageEl) {
            return;
        }
        if (this.hoveredImageEl) {
            this.hoveredImageEl.dispatchEvent(new MouseEvent("mouseleave", { view: window }));
        }
        if (nextHoveredImageEl) {
            nextHoveredImageEl.dispatchEvent(new MouseEvent("mouseenter", { view: window }));
        }

        this.hoveredImageEl = nextHoveredImageEl;
    }
}

registry.category("public.interactions").add("website.clickable_card", ClickableCard);
