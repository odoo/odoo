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
            // Filter to exclude cover images coming from nested cards
            const coverImageWrapper = [
                ...editingElement.querySelectorAll(".o_card_img_wrapper"),
            ].filter((node) => node.closest(".s_card") === editingElement)[0];
            const hasCoverImage = !!coverImageWrapper;
            const imageToWrapperRatio = hasCoverImage
                ? this.getImageToWrapperRatio(coverImageWrapper)
                : null;
            const hasShape = hasCoverImage
                ? !!coverImageWrapper.querySelector(".o_card_img[data-shape]")
                : false;
            // Sometimes the imageToWrapperRatio is very close to but not
            // exactly 1. In this case, the image alignment slider would have no
            // visible effect on the actual alignment. To avoid the slider to
            // spawn in this case, we use a loose comparison.
            const hasSquareRatio = Math.abs(imageToWrapperRatio - 1) < 0.001;
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
    getImageToWrapperRatio(imageWrapperEl) {
        const imageEl = imageWrapperEl.querySelector(".o_card_img");
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
