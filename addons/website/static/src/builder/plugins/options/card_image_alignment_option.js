/** @odoo-module native */
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";

const log = makeLogger("website.builder.option.card_image_alignment_option");

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
        useLifecycleLog(log);
        this.state = useDomState(async (editingElement) => {
            await this.waitForAllImageloaded(this.env.getEditingElements());
            const coverImageWrapperEl = editingElement.querySelector(
                ":scope > .o_card_img_wrapper",
            );
            const hasCoverImage = !!coverImageWrapperEl;
            const imageToWrapperRatio = hasCoverImage
                ? this.getImageToWrapperRatio(coverImageWrapperEl)
                : null;
            const hasShape = hasCoverImage
                ? !!coverImageWrapperEl.querySelector(".o_card_img[data-shape]")
                : false;
            const hasSquareRatio = Math.abs(imageToWrapperRatio - 1) < 0.001;
            return {
                imageToWrapperRatio,
                show: hasCoverImage && !(hasSquareRatio || hasShape),
            };
        });
    }

    /**
     * @param {HTMLElement} editingElement
     * @returns {number|null}
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
                            imageEl.addEventListener("load", () => resolve(), {
                                once: true,
                            });
                            imageEl.addEventListener("error", () => resolve(), {
                                once: true,
                            });
                        }),
                    );
                }
            }
        }
        await Promise.all(promises);
    }
}
