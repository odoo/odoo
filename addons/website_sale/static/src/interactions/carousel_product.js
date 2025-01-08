import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";

export class CarouselProduct extends Interaction {
    static selector = "#o-carousel-product";
    dynamicContent = {
        _root: {
            "t-on-slide.bs.carousel.noupdate": this.onSlideCarouselProduct,
            "t-att-style": () => ({
                "top": this.top,
            }),
        },
        _window: {
            "t-on-resize.noupdate": this.throttled(this.onSlideCarouselProduct),
        },
        ".carousel-indicators": {
            "t-att-style": () => ({
                "justify-content": this.indicatorJustify,
            }),
        },
        ".o_carousel_product_indicators": {
            "t-on-wheel.prevent": this.onMouseWheel,
        },
    };

    setup() {
        this.top = undefined;
        this.indicatorJustify = "start";
    }
    start() {
        this.updateCarouselPosition();
        this.registerCleanup(this.services.website_menus.registerCallback(this.updateCarouselPosition.bind(this)));
        if (this.el.querySelector(".carousel-indicators")) {
            this.updateJustifyContent();
        }
    }

    updateCarouselPosition() {
        let size = 5;
        for (const el of document.querySelectorAll(".o_top_fixed_element")) {
            const style = window.getComputedStyle(el);
            size += el.getBoundingClientRect().height + parseFloat(style.marginTop) + parseFloat(style.marginBottom);
        }
        this.top = size;
    }

    /**
     * Center the selected indicator to scroll the indicators list when it
     * overflows.
     *
     * @param {Event} ev
     */
    onSlideCarouselProduct(ev) {
        const isReversed = this.el.style["flex-direction"] === "column-reverse";
        const isLeftIndicators = this.el.classList.contains("o_carousel_product_left_indicators");
        const indicatorsDivEl = this.el.querySelector(isLeftIndicators ? ".o_carousel_product_indicators" : ".carousel-indicators");
        if (!indicatorsDivEl) {
            return;
        }
        const isVertical = isLeftIndicators && !isReversed;
        const currentIndicatorEl = ev?.relatedTarget || this.el.querySelector("li.active");
        let indicatorIndex = currentIndicatorEl ? [...currentIndicatorEl.parentElement.children].findIndex(el => el === currentIndicatorEl) : -1;
        const indicatorEl = indicatorsDivEl.querySelector(`[data-bs-slide-to="${indicatorIndex}"]`);
        const indicatorsDivRect = indicatorsDivEl.getBoundingClientRect();
        const indicatorsDivStyle = window.getComputedStyle(indicatorsDivEl);
        const indicatorsDivSize = isVertical ? indicatorsDivRect.height + parseFloat(indicatorsDivStyle.marginTop) + parseFloat(indicatorsDivStyle.marginBottom) : indicatorsDivRect.width + parseFloat(indicatorsDivStyle.marginLeft) + parseFloat(indicatorsDivStyle.marginRight);
        const indicatorRect = indicatorEl.getBoundingClientRect();
        const indicatorStyle = window.getComputedStyle(indicatorEl);
        const indicatorSize = isVertical ? indicatorRect.height : indicatorRect.width;
        const indicatorPosition = isVertical ? indicatorRect.top - indicatorsDivRect.top - parseFloat(indicatorStyle.marginTop) : indicatorRect.left - indicatorsDivRect.left - parseFloat(indicatorStyle.marginLeft);
        const scrollSize = isVertical ? indicatorsDivEl.scrollHeight : indicatorsDivEl.scrollWidth;
        let indicatorsPositionDiff = (indicatorPosition + (indicatorSize / 2)) - (indicatorsDivSize / 2);
        indicatorsPositionDiff = Math.min(indicatorsPositionDiff, scrollSize - indicatorsDivSize);
        this.updateJustifyContent();
        this.updateContent();
        const indicatorsPositionX = isVertical ? "0" : "-" + indicatorsPositionDiff;
        const indicatorsPositionY = isVertical ? "-" + indicatorsPositionDiff : "0";
        const translate3D = indicatorsPositionDiff > 0 ? "translate3d(" + indicatorsPositionX + "px," + indicatorsPositionY + "px,0)" : "";
        indicatorsDivEl.style.setProperty("transform", translate3D);
    }
    updateJustifyContent() {
        this.indicatorJustify = "start";
        if (uiUtils.getSize() <= SIZES.MD) {
            const indicatorsDivEl = this.el.querySelector(".carousel-indicators");
            const indicatorsDivRect = indicatorsDivEl.getBoundingClientRect();
            const lastIndicatorEl = indicatorsDivEl.children[indicatorsDivEl.children.length - 1];
            const lastIndicatorRect = lastIndicatorEl.getBoundingClientRect();
            const lastIndicatorStyle = window.getComputedStyle(lastIndicatorEl);
            const firstLiEl = indicatorsDivEl.querySelector("li");
            const firstLiRect = firstLiEl.getBoundingClientRect();
            if ((lastIndicatorRect.left - indicatorsDivRect.left - parseFloat(lastIndicatorStyle.marginLeft) + firstLiRect.width) < indicatorsDivRect.width) {
                this.indicatorJustify = "center";
            }
        }
    }
    /**
     * @param {Event} ev
     */
    onMouseWheel(ev) {
        const bsCarousel = window.Carousel.getOrCreateInstance(this.el);
        if (ev.deltaY > 0) {
            bsCarousel.next();
        } else {
            bsCarousel.prev();
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale.carousel_product", CarouselProduct);

registry
    .category("public.interactions.edit")
    .add("website_sale.carousel_product", {
        Interaction: CarouselProduct,
    });
