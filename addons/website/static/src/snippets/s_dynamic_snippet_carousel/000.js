import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/000";


export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
    }

    getQWebRenderOptions() {
        return Object.assign(
            super.getQWebRenderOptions(...arguments),
            {
                interval: parseInt(this.el.dataset.carouselInterval),
                rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || '',
            },
        );
    }
}

registry.category("website.active_elements").add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
