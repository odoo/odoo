import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class CardImageAlignmentOption extends BaseOptionComponent {
    static template = "website.CardImageAlignmentOption";
    static props = {
        label: { type: String },
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 0,
    };

    setup() {
        super.setup();
        this.state = useDomState(async (editingElement) => {
            await this.waitForAllImageloaded(this.env.getEditingElements());
            const imageToWrapperRatio = this.getImageToWrapperRatio(editingElement);
            const hasCoverImage = !!editingElement.querySelector(".o_card_img_wrapper");
            // Sometimes the imageToWrapperRatio is very close to but not
            // exactly 1. In this case, the image alignment slider would have no
            // visible effect on the actual alignment. To avoid the slider to
            // spawn in this case, we use a loose comparison.
            const hasSquareRatio = Math.abs(imageToWrapperRatio - 1) < 0.001;
            const hasShape = !!editingElement.querySelector(".o_card_img[data-shape]");
            return {
                imageToWrapperRatio,
                show: hasCoverImage && !(hasSquareRatio || hasShape),
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

    async waitForAllImageloaded(editingElements) {
        const promises = [];
        for (const editingEl of editingElements) {
            const imageEls = editingEl.matches("img")
                ? [editingEl]
                : editingEl.querySelectorAll("img");
            for (const imageEl of imageEls) {
                if (!imageEl.complete) {
                    promises.push(
                        new Promise((resolve) => {
                            imageEl.addEventListener("load", () => resolve());
                        })
                    );
                }
            }
        }
        await Promise.all(promises);
    }
}
