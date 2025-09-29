import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { TranslateImageOption } from "@website/builder/plugins/translation/options/media_translation_option";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = ["translation"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [TranslateImageOption],
        builder_actions: {
            TranslateMediaSrcAction,
        },
    };
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["imagePostProcess", "imageToolOption", "media"];

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
        };
    }

    async apply({ editingElement, params: { mainParam: mediaType } }) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: mediaType === "images",
                noImages: mediaType !== "images",
                visibleTabs: [mediaType.toUpperCase()],

                node: editingElement,
                save: async (newMediaEl) => {
                    await this.savingMap[mediaType](editingElement, newMediaEl);
                },
            });
            onClose.then(resolve);
        });
    }
    /**
     * @param {HTMLElement} el - element whose attribute is translated
     * @param {string} translation - new translation
     * @param {string} originalText - text before the new translation
     * @param {string} attribute - attribute to update in the translation map
     */
    handleTranslationMapHistory(el, translation, originalText, attribute) {
        const updateTranslationMap = this.dependencies.translation.updateTranslationMap;
        this.dependencies.history.applyCustomMutation({
            apply: () => {
                updateTranslationMap(el, translation, attribute);
            },
            revert: () => {
                updateTranslationMap(el, originalText, attribute);
            },
        });
    }

    async saveImage(editingElement, newImgEl) {
        // TODO @image-translate: this is a one-to-one "translation" of the
        // image. We bring back from the original image all the manipulations
        // that have been done: shape, resizing, filters... But if the image is
        // different, those options should also be adaptable. We should have
        // translation options to handle the new image exactly like what is
        // possible in the builder.
        const attributesToKeep = ["oeTranslationState"];
        const newDataset = { ...editingElement.dataset, ...newImgEl.dataset };
        for (const dataAttribute in newDataset) {
            if (attributesToKeep.includes(dataAttribute)) {
                newDataset[dataAttribute] = editingElement.dataset[dataAttribute];
            } else {
                if (dataAttribute in newImgEl.dataset) {
                    editingElement.dataset[dataAttribute] = newDataset[dataAttribute];
                } else {
                    delete newDataset[dataAttribute];
                    delete editingElement.dataset[dataAttribute];
                }
            }
        }
        const originalSrc = editingElement.getAttribute("src");
        const translatedSrc = newImgEl.getAttribute("src");
        editingElement.setAttribute("src", translatedSrc);
        const updateImageAttributes = await this.dependencies.imagePostProcess.processImage({
            img: editingElement,
            newDataset,
            onImageInfoLoaded: (dataset) =>
                this.dependencies.imageToolOption.onImageInfoLoaded(editingElement, dataset),
        });
        updateImageAttributes();

        this.handleTranslationMapHistory(
            editingElement,
            translatedSrc,
            originalSrc,
            "data-oe-translatable-link"
        );
        editingElement.classList.add("oe_translated");
        this.dispatchTo("on_replaced_media_handlers", { newMediaEl: editingElement });
    }
}
