import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class CardImageOption extends BaseOptionComponent {
    static template = "html_builder.CardImageOption";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const imageToWrapperRatio = this.getImageToWrapperRatio(editingElement);
            return {
                hasCoverImage: !!editingElement.querySelector(".o_card_img_wrapper"),
                hasSquareRatio: imageToWrapperRatio === 1,
                imageToWrapperRatio,
                hasShape: !!editingElement.querySelector(".o_card_img[data-shape]"),
            };
        });
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
