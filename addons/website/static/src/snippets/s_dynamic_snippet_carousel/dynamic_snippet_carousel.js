import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { utils as uiUtils } from "@web/core/ui/ui_service";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";
    dynamicContent = {
        _root: {
            't-on-slid.bs.carousel': this.onSlidCarousel,
        }
    }

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
        this.preloadCarouselItems();
    }

    getQWebRenderOptions() {
        return Object.assign(
            super.getQWebRenderOptions(...arguments),
            {
                interval: parseInt(this.el.dataset.carouselInterval),
                rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || "",
                scrollMode: this.el.dataset.scrollMode || '',
                carouselWrap: this.el.dataset.carouselWrap || 'false',
            },
        );
    }

    /**
     * Executes when the carousel ends sliding.
     *
     */
    onSlidCarousel(event) {
        this.preloadCarouselItems();
    }

    /**
     * Preloads next and prev carousel items to avoid animation lag
     *
     */
    preloadCarouselItems(){
        const activeCarouselItemEl = this.el.querySelector('.carousel-item.active');
        if (activeCarouselItemEl) {
            const carouselItemArray = [
                activeCarouselItemEl.previousElementSibling || this.el.querySelector('.carousel-item:last-child'),
                activeCarouselItemEl.nextElementSibling || this.el.querySelector('.carousel-item:first-child')
            ];

            carouselItemArray.forEach(carouselItemEl => {
                carouselItemEl.querySelectorAll('img[loading="lazy"]').forEach(img => {
                    img.setAttribute('loading', 'eager');
                });
            });
        }
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);

registry
    .category("public.interactions.edit")
    .add("website.dynamic_snippet_carousel", {
        Interaction: DynamicSnippetCarousel,
    });
