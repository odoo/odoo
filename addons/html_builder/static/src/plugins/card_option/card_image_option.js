import { useDomState, useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";

export class CardImageOption extends Component {
    static template = "html_builder.CardImageOption";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
        this.state = useDomState((editingElement) => {
            const imageToWrapperRatio = this.getImageToWrapperRatio(editingElement);
            return {
                hasCoverImage: !!editingElement.querySelector(".o_card_img_wrapper"),
                hasSquareRatio: imageToWrapperRatio === 1,
                imageToWrapperRatio,
                hasShape: !!editingElement.querySelector(".o_card_img[data-shape]"),
            };
        });
        this.isActiveItem = useIsActiveItem();
    }

    /**
     * Compares the aspect ratio of the card image to its wrapper.
     *
     * @param {HTMLElement} editingElement
     * @returns {number|null} Ratio comparison value:
     *                   -  1: img and wrapper have identical aspect ratios
     *                   - <1: img is more portrait (taller) than wrapper
     *                   - >1: img is more landscape (wider) than wrapper
     */
    getImageToWrapperRatio(editingElement) {
        const imageEl = editingElement.querySelector(".o_card_img");
        const imageWrapperEl = editingElement.querySelector(".o_card_img_wrapper");
        if (!imageEl || !imageWrapperEl) {
            return null;
        }
        const imgRatio = imageEl.naturalWidth / imageEl.naturalHeight;
        const wrapperRatio = imageWrapperEl.offsetWidth / imageWrapperEl.offsetHeight;
        return imgRatio / wrapperRatio;
    }
}
