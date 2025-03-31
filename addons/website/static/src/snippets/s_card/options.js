/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import options from "@web_editor/js/editor/snippets.options";


options.registry.CardWidth = options.Class.extend({
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const value = await this._super(...arguments);
        if (methodName === "selectStyle") {
            if (params.cssProperty === "max-width") {
                // If no `max-width` is set, consider it to be at 100%.
                if (!this.$target[0].style[params.cssProperty]) {
                    return "100%";
                }
            }
        } else if (methodName === "selectClass" && !value) {
            // If no alignment has been set, consider it to be set to the left.
            return "me-auto";
        }
        return value;
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === "card_alignment_opt") {
            const maxWidth = this.$target[0].style.maxWidth;
            const isFullWidth = !maxWidth || maxWidth === "100%";
            return !isFullWidth;
        }
        return this._super(...arguments);
    },
});

options.registry.CardImageOptions = options.Class.extend({
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Injects a new cover image.
     */
    addCoverImage() {
        const imageWrapperEl = renderToElement("website.s_card.imageWrapper");
        this.$target[0].insertAdjacentElement("afterbegin", imageWrapperEl);
        this.$target[0].classList.add("o_card_img_top");
    },
    /**
     * Changes the cover image position.
     *
     * @see this.selectClass for parameters
     */
    selectImageClass(previewMode, widgetValue, params) {
        const imageEl = this.$target[0].querySelector(".o_card_img");
        for (const className of params.possibleValues) {
            if (className) {
                imageEl.classList.remove(className);
            }
        }
        imageEl.classList.add(widgetValue);

        // Removing invalid ratio classes when changing the image position.
        const imageWrapperEl = this.$target[0].querySelector(".o_card_img_wrapper");
        if (previewMode === true) {
            // If the image has a non-square ratio, force the ratio to be square
            // when setting the image as horizontal, as only the "Square" ratio
            // is available in that case (so the "Ratio" widget is consistent).
            if (["rounded-start", "rounded-end"].includes(widgetValue)
                    && this.$target[0].querySelector(".ratio:not(.ratio-1x1)")) {
                const ratioClassRegex = /(ratio-4x3|ratio-16x9|ratio-21x9|o_card_img_ratio_custom)/g;
                const ratioClass = imageWrapperEl.className.match(ratioClassRegex);
                if (ratioClass) {
                    this.previousRatio = ratioClass[0];
                    imageWrapperEl.classList.remove(this.previousRatio);
                    imageWrapperEl.classList.add("ratio-1x1");
                }
            }
        } else if (previewMode === false) {
            delete this.previousRatio;
        } else {
            if (this.previousRatio) {
                imageWrapperEl.classList.remove("ratio-1x1");
                imageWrapperEl.classList.add(this.previousRatio);
                delete this.previousRatio;
            }
        }
    },
    /**
     * Removes the cover image.
     */
    removeCoverImage() {
        const imageWrapperEl = this.$target[0].querySelector(".o_card_img_wrapper");
        imageWrapperEl.remove();

        // Remove the classes and styles linked to the wrapper .
        const imageWrapperClasses = ["o_card_img_top", "o_card_img_horizontal", "flex-lg-row", "flex-lg-row-reverse"];
        this.$target[0].classList.remove(...imageWrapperClasses);
        this.$target[0].style.removeProperty("--card-img-size-h");
        this.$target[0].style.removeProperty("--card-img-ratio-align");
        this.$target[0].style.removeProperty("--card-img-aspect-ratio");
    },
    /**
     * Aligns the image inside the cover.
     *
     * @private
     */
    alignCoverImage() {
        const ratio = this._getImageToWrapperRatio();
        const imageWrapperEl = this.$target[0].querySelector(".o_card_img_wrapper");

        imageWrapperEl.classList.toggle("o_card_img_adjust_v", ratio > 1);
        imageWrapperEl.classList.toggle("o_card_img_adjust_h", ratio < 1);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        const hasCoverImage = !!this.$target[0].querySelector(".o_card_img_wrapper");
        const useRatio = !!this.$target[0].querySelector(".o_card_img_wrapper.ratio");
        const hasNonSquareRatio = this._getImageToWrapperRatio() !== 1;
        const hasShape = !!this.$target[0].querySelector(".o_card_img[data-shape]");

        if (widgetName === "add_cover_image_opt") {
            return !hasCoverImage;
        } else if (["cover_image_position_opt", "remove_cover_image_opt", "cover_image_width_opt",
                "cover_image_ratio_range_opt"].includes(widgetName)) {
            return hasCoverImage;
        } else if (widgetName === "cover_image_alignment_opt") {
            return hasCoverImage && hasNonSquareRatio && useRatio && !hasShape;
        }
        return this._super(...arguments);
    },
    /**
     * Compares the aspect ratio of the card image to its wrapper.
     *
     * @private
     * @returns {number} Ratio comparison value:
     *                   -  1: img and wrapper have identical aspect ratios
     *                   - <1: img is more portrait (taller) than wrapper
     *                   - >1: img is more landscape (wider) than wrapper
     */
    _getImageToWrapperRatio() {
        const imageEl = this.$target[0].querySelector(".o_card_img");
        const imageWrapperEl = this.$target[0].querySelector(".o_card_img_wrapper");
        if (!imageEl || !imageWrapperEl) {
            return false;
        }

        const imgRatio = imageEl.naturalHeight / imageEl.naturalWidth;
        const wrapperRatio = imageWrapperEl.offsetHeight / imageWrapperEl.offsetWidth;

        return imgRatio / wrapperRatio;
    },
});
