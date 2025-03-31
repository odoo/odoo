import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

const ratiosOnlySupportedForTopImage = [
    "ratio ratio-4x3",
    "ratio ratio-16x9",
    "ratio ratio-21x9",
    "ratio o_card_img_ratio_custom",
];
const imageRelatedClasses = [
    "o_card_img_top",
    "o_card_img_horizontal",
    "flex-lg-row",
    "flex-lg-row-reverse",
];
const imageRelatedStyles = [
    "--card-img-aspect-ratio",
    "--card-img-size-h",
    "--card-img-ratio-align",
];

class CardImageOptionPlugin extends Plugin {
    static id = "cardImageOption";
    static dependencies = ["remove"];
    resources = {
        builder_actions: {
            setCoverImagePosition: {
                apply: ({ editingElement, param: { mainParam: className } }) => {
                    const imageEl = editingElement.querySelector(".o_card_img");
                    imageEl.classList.add(className);
                    this.adaptRatio(editingElement, className);
                },
                clean: ({ editingElement, param: { mainParam: className } }) => {
                    const imageEl = editingElement.querySelector(".o_card_img");
                    imageEl.classList.remove(className);
                },
            },
            removeCoverImage: {
                apply: ({ editingElement }) => {
                    const imageWrapper = editingElement.querySelector(".o_card_img_wrapper");
                    this.dependencies.remove.removeElement(imageWrapper);
                    editingElement.classList.remove(...imageRelatedClasses);
                    imageRelatedStyles.forEach((prop) => editingElement.style.removeProperty(prop));
                },
            },
            addCoverImage: {
                apply: ({ editingElement }) => {
                    const imageWrapper = renderToElement("html_builder.s_card.imageWrapper");
                    editingElement.prepend(imageWrapper);
                    editingElement.classList.add("o_card_img_top");
                },
            },
            alignCoverImage: {
                apply: ({ editingElement, param: { mainParam: direction } }) => {
                    const imgWrapper = editingElement.querySelector(".o_card_img_wrapper");
                    imgWrapper.classList.toggle("o_card_img_adjust_v", direction === "vertical");
                    imgWrapper.classList.toggle("o_card_img_adjust_h", direction === "horizontal");
                },
            },
        },
    };

    /**
     * Change unsupported ratios to the square ratio when the cover image is
     * positioned horizontally.
     */
    adaptRatio(editingElement, imagePositionClass) {
        if (imagePositionClass === "card-img-top") {
            // All ratios are supported for top image
            return;
        }
        const imageWrapper = editingElement.querySelector(".o_card_img_wrapper");
        const asMainParam = (mainParam) => ({ editingElement: imageWrapper, param: { mainParam } });
        for (const ratioClasses of ratiosOnlySupportedForTopImage) {
            if (classAction.isApplied(asMainParam(ratioClasses))) {
                classAction.clean(asMainParam(ratioClasses));
                // Only square ratio is supported for horizontal image
                classAction.apply(asMainParam("ratio ratio-1x1"));
                return;
            }
        }
    }
}

registry.category("website-plugins").add(CardImageOptionPlugin.id, CardImageOptionPlugin);
