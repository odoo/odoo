import { BaseHeaderSpecial } from "@website/interactions/header/base_header_special";
import { registry } from "@web/core/registry";

export class HeaderFadeOut extends BaseHeaderSpecial {
    static selector = "header.o_header_fade_out:not(.o_header_sidebar)";

    setup() {
        super.setup();
        this.isAnimated = true;
        this.el.style.transitionDuration = "400ms";
        this.el.style.transitionProperty = "opacity";
        this.fadeTimeout = null;
    }

    transformShow() {
        this.el.style.opacity = 1;
        if (this.fadeTimeout) {
            clearTimeout(this.fadeTimeout);
        }
        super.transformShow();
    }

    /**
     * @override
     */
    getCoveredBottom() {
        // Shown or hidden by fading, and only moved once invisible: cover the
        // page proportionally to the current opacity so that what is placed
        // below follows the fading. The opacity is only considered once set
        // by the interaction, so that a custom style does not reduce it.
        const opacity = this.el.style.opacity ? parseFloat(getComputedStyle(this.el).opacity) : 1;
        return super.getCoveredBottom() * opacity;
    }

    transformHide() {
        this.el.style.opacity = 0;
        this.isVisible = false;
        // We want to translate the header after the transition is complete
        this.fadeTimeout = this.waitForTimeout(
            () => (this.transformValue = "translate(0, -100%)"),
            400
        );
        this.adaptToHeaderChangeLoop(1);
    }
}

registry.category("public.interactions").add("website.header_fade_out", HeaderFadeOut);

registry.category("public.interactions.edit").add("website.header_fade_out", {
    Interaction: HeaderFadeOut,
});
