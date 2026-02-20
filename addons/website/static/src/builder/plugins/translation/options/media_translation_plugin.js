import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    TranslateDocumentOption,
    TranslateImageOption,
    TranslateVideoOption,
} from "@website/builder/plugins/translation/options/media_translation_option";

/**
 * @typedef { Object } MediaTranslationShared
 * @property { MediaTranslationPlugin['translateMedia'] } translateMedia
 */

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = [
        "history",
        "imagePostProcess",
        "imageToolOption",
        "media",
        "media_website",
        "translation",
    ];
    static shared = ["translateMedia"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [TranslateImageOption, TranslateVideoOption, TranslateDocumentOption],
        builder_actions: {
            TranslateMediaSrcAction,
        },
    };

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
            videos: this.saveVideo.bind(this),
            documents: this.saveDocument.bind(this),
        };
        const translatableMediaSelector = [
            TranslateDocumentOption.selector,
            TranslateImageOption.selector,
            TranslateVideoOption.selector,
        ].join(", ");

        this.addDomListener(this.editable, "dblclick", async (ev) => {
            const targetEl = ev.target.closest(translatableMediaSelector);
            if (!targetEl) {
                return;
            }
            if (this.isReplaceableMedia(targetEl)) {
                const mediaType = this.getMediaType(targetEl);
                this.dependencies.media_website.onDblClickEditableMedia(targetEl, async () => {
                    await this.translateMedia(targetEl, mediaType);
                });
            }
        });
        this.addDomListener(this.editable, "click", (ev) => {
            const targetEl = ev.target.closest(translatableMediaSelector);
            if (!targetEl) {
                return;
            }
            if (this.isReplaceableMedia(targetEl)) {
                this.dependencies.media_website.openImageTooltip(targetEl);
            }
        });
    }

    getMediaType(el) {
        if (el.matches(TranslateImageOption.selector)) {
            return "images";
        }
        if (el.matches(TranslateVideoOption.selector)) {
            return "videos";
        }
        if (el.matches(TranslateDocumentOption.selector)) {
            return "documents";
        }
    }
    /**
     * @param {HTMLElement} mediaEl
     * @returns {Boolean}
     */
    isReplaceableMedia(mediaEl) {
        if (this.getMediaType(mediaEl) === "documents") {
            return true;
        }
        // An element marked `.o_translatable_attribute` means that it went
        // through `findOEditable` and `buildTranslationInfoMap` in the
        // TranslationPlugin. We can rely on that information.
        return mediaEl.classList.contains("o_translatable_attribute");
    }
    /**
     * Opens the media dialog to translate the source of the media.
     * @param {HTMLElement} element - element that should be "translated"
     * @param {"images" | "videos" | "documents"} mediaType
     */
    async translateMedia(element, mediaType) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: mediaType === "images",
                noImages: mediaType !== "images",
                visibleTabs: [mediaType.toUpperCase()],

                node: element,
                save: async (newMediaEl) => {
                    await this.savingMap[mediaType](element, newMediaEl);
                    this.dependencies.history.addStep(); // Needed for the dblclick
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

    saveVideo(editingElement, newVideoEl) {
        const originalSrc =
            this.dependencies.translation.getTranslationInfo(editingElement)["data-oe-expression"]
                .translation;
        const newSrc = newVideoEl.querySelector("iframe").getAttribute("src");
        editingElement.setAttribute("data-oe-expression", newSrc);
        editingElement.querySelector("iframe").setAttribute("src", newSrc);
        editingElement.classList.add("oe_translated");

        this.handleTranslationMapHistory(editingElement, newSrc, originalSrc, "data-oe-expression");
    }

    saveDocument(editingElement, newFileEl) {
        editingElement.replaceChildren(...newFileEl.children);
        editingElement.dataset.attachmentId = newFileEl.dataset.attachmentId;
        editingElement.querySelector("a.o_link_readonly").classList.add("o_translate_inline");
    }
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["mediaTranslation"];

    async apply({ editingElement, params: { mainParam: mediaType } }) {
        await this.dependencies.mediaTranslation.translateMedia(editingElement, mediaType);
    }
}
