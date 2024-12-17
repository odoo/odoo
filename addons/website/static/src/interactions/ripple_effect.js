import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class RippleEffect extends Interaction {
    static selector = ".btn, .dropdown-toggle, .dropdown-item";
    dynamicContent = {
        "_root": {
            "t-on-click": this.onClick,
            "t-att-class": () => ({
                "o_js_ripple_effect": this.isActive,
            }),
        },
    };
    duration = 350;

    setup() {
        this.isActive = false;
        this.rippleEl = null;
        this.timeoutID = null;
    }
    destroy() {
        this.rippleEl?.remove();
    }

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (!this.rippleEl) {
            this.rippleEl = document.createElement("span");
            this.rippleEl.classList.add("o_ripple_item");
            this.rippleEl.style.animationDuration = `${this.duration}ms`;
            this.el.appendChild(this.rippleEl);
        }

        clearTimeout(this.timeoutID);
        if (this.isActive) {
            this.isActive = false;
            this.updateContent();
        }

        const rect = this.el.getBoundingClientRect();
        const offsetY = rect.top + window.scrollY;
        const offsetX = rect.left + window.scrollX;
        // The diameter need to be recomputed because a change of window width
        // can affect the size of a button (e.g. media queries).
        const diameter = Math.max(this.el.clientWidth, this.el.clientHeight);

        this.rippleEl.style.width = `${diameter}px`;
        this.rippleEl.style.height = `${diameter}px`;
        this.rippleEl.style.top = `${ev.pageY - offsetY - diameter / 2}px`;
        this.rippleEl.style.left = `${ev.pageX - offsetX - diameter / 2}px`;

        this.isActive = true;
        this.timeoutID = this.waitForTimeout(() => {
            this.isActive = false;
        }, this.duration);
    }
}

registry
    .category("public.interactions")
    .add("website.ripple_effect", RippleEffect);
