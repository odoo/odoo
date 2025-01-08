import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class SlideTogglePreview extends Interaction {
    static selector = ".o_wslides_js_slide_toggle_is_preview";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.toggleSlidePreview,
            "t-att-class": () => ({
                "text-bg-success": this.isPreview,
                "text-bg-light": !this.isPreview,
                "badge-hide": !this.isPreview,
                "border": !this.isPreview,
            }),
        },
    };

    setup() {
        this.isPreview = false;
    }

    async toggleSlidePreview() {
        const isPreview = await this.waitFor(rpc('/slides/slide/toggle_is_preview', { slide_id: this.el.dataset.slideId }));
        this.isPreview = !!isPreview;
    }
}

registry
    .category("public.interactions")
    .add("website_slides.slide_toggle_preview", SlideTogglePreview);
