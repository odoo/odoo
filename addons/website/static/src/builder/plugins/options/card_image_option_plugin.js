import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { ImagePositionOverlay } from "@html_builder/plugins/image/image_position_overlay";
import { onceAllImagesLoaded } from "@website/utils/images";

/**
 * @typedef { Object } CardImageOptionShared
 * @property { CardImageOptionPlugin['adaptRatio'] } adaptRatio
 */

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
    "--card-img-ratio-align", // kept for compatibility
];

class CardImageOptionPlugin extends Plugin {
    static id = "cardImageOption";
    static dependencies = ["remove", "history", "builderOptions"];
    static shared = ["adaptRatio", "getDelta"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCoverImagePositionAction,
            RemoveCoverImageAction,
            AddCoverImageAction,
            CoverImagePositionOverlayAction,
        },
    };

    setup() {
        super.setup();
        this.classAction = new ClassAction(this);
    }
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
        const asMainParam = (mainParam) => ({
            editingElement: imageWrapper,
            params: { mainParam },
        });
        for (const ratioClasses of ratiosOnlySupportedForTopImage) {
            if (this.classAction.isApplied(asMainParam(ratioClasses))) {
                this.classAction.clean(asMainParam(ratioClasses));
                // Only square ratio is supported for horizontal image
                this.classAction.apply(asMainParam("ratio ratio-1x1"));
                return;
            }
        }
    }

    getDelta(imageEl) {
        const naturalWidth = imageEl.naturalWidth;
        const naturalHeight = imageEl.naturalHeight;
        const { width, height, paddingLeft, paddingRight, paddingTop, paddingBottom } =
            getComputedStyle(imageEl);
        const imageElWidth = parseFloat(width) - parseFloat(paddingLeft) - parseFloat(paddingRight);
        const imageElHeight =
            parseFloat(height) - parseFloat(paddingTop) - parseFloat(paddingBottom);
        const renderRatio = Math.max(imageElWidth / naturalWidth, imageElHeight / naturalHeight);
        return {
            x: Math.round(imageElWidth - renderRatio * naturalWidth),
            y: Math.round(imageElHeight - renderRatio * naturalHeight),
        };
    }
}

export class SetCoverImagePositionAction extends BuilderAction {
    static id = "setCoverImagePosition";
    static dependencies = ["cardImageOption"];
    apply({ editingElement, params: { mainParam: className } }) {
        const imageEl = editingElement.querySelector(".o_card_img");
        imageEl.classList.add(className);
        this.dependencies.cardImageOption.adaptRatio(editingElement, className);
    }
    clean({ editingElement, params: { mainParam: className } }) {
        const imageEl = editingElement.querySelector(".o_card_img");
        imageEl.classList.remove(className);
    }
}
export class RemoveCoverImageAction extends BuilderAction {
    static id = "removeCoverImage";
    static dependencies = ["history", "builderOptions", "remove"];
    apply({ editingElement }) {
        const imageWrapperEl = editingElement.querySelector(".o_card_img_wrapper");
        imageWrapperEl.remove();
        // Remove the classes and styles linked to the wrapper.
        editingElement.classList.remove(...imageRelatedClasses);
        imageRelatedStyles.forEach((prop) => editingElement.style.removeProperty(prop));
    }
}
export class AddCoverImageAction extends BuilderAction {
    static id = "addCoverImage";
    apply({ editingElement }) {
        const imageWrapper = renderToElement("website.s_card.imageWrapper");
        editingElement.prepend(imageWrapper);
        editingElement.classList.add("o_card_img_top");
    }
}
export class CoverImagePositionOverlayAction extends BuilderAction {
    static id = "coverImagePositionOverlay";
    static dependencies = ["overlayButtons", "history", "cardImageOption"];
    setup() {
        this.withLoadingEffect = false;
    }
    async load({ editingElement }) {
        const imageEl = editingElement.querySelector(".o_card_img");
        await onceAllImagesLoaded(imageEl);
        this.dependencies.overlayButtons.hideOverlayButtonsUi();
        return new Promise((resolve) => {
            const removeOverlay = this.services.overlay.add(
                ImagePositionOverlay,
                {
                    targetEl: imageEl,
                    close: (position) => {
                        removeOverlay();
                        resolve(position);
                    },
                    onDrag: (percentPosition) => {
                        imageEl.style.objectPosition = `${percentPosition.left}% ${percentPosition.top}%`;
                    },
                    getDelta: () => this.dependencies.cardImageOption.getDelta(imageEl),
                    getPosition: () => getComputedStyle(imageEl).objectPosition,
                    editable: this.editable,
                    history: {
                        makeSavePoint: this.dependencies.history.makeSavePoint,
                    },
                },
                { onRemove: () => this.dependencies.overlayButtons.showOverlayButtonsUi() }
            );
        });
    }
    apply({ editingElement, loadResult }) {
        if (loadResult) {
            editingElement.querySelector(".o_card_img").style.objectPosition = loadResult;
        }
    }
}

registry.category("website-plugins").add(CardImageOptionPlugin.id, CardImageOptionPlugin);
