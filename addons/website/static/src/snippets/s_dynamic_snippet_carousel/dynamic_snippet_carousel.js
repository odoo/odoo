import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { utils as uiUtils } from "@web/core/ui/ui_service";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
    }

    getQWebRenderOptions() {
        const scrollMode = this.el.classList.contains("o_carousel_multi_items") ? "single" : "all";
        return Object.assign(super.getQWebRenderOptions(...arguments), {
            interval: parseInt(this.el.dataset.carouselInterval),
            rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
            arrowPosition: this.el.dataset.arrowPosition || "",
            scrollMode: scrollMode,
        });
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
