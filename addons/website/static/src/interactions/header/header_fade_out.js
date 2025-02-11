import { BaseHeaderSpecial } from "@website/interactions/header/base_header_special";
import { registry } from "@web/core/registry";

export class HeaderFadeOut extends BaseHeaderSpecial {
    static selector = "header.o_header_fade_out:not(.o_header_sidebar)";

    setup() {
        super.setup();
        this.isAnimated = true;
        this.el.style.transitionDuration = "400ms";
        this.el.style.transitionProperty = 'opacity';
    }

    transformShow() {
        this.el.style.opacity = 1;
        super.transformShow();
    }

    transformHide() {
        this.el.style.opacity = 0;
        this.isVisible = false;
        // We want to translate the header after the transition is complete
        this.waitForTimeout(() => this.el.style.transform = "translate(0, -100%)", 400);
        this.adaptToHeaderChangeLoop(1);
    }
}

registry
    .category("public.interactions")
    .add("website.header_fade_out", HeaderFadeOut);

registry
    .category("public.interactions.edit")
    .add("website.header_fade_out", {
        Interaction: HeaderFadeOut,
    });
