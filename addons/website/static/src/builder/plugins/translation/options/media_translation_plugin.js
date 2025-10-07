import { BuilderAction } from "@html_builder/core/builder_action";
import { getMimetypeBeforeShape } from "@html_builder/utils/image";
import { isImageSupportedForProcessing } from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = ["imagePostProcess"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            TranslateMediaSrcAction,
        },
        on_get_dirty_translations_handlers: this.registerImageDirtyTranslations.bind(this),
        on_image_saved_handlers: this.updateTranslationsOnImageSaved.bind(this),
        on_will_save_media_dialog_handlers: withSequence(
            5,
            this.onWillSaveMediaDialogHandlers.bind(this)
        ),
        // As long as image options are not available in translation, prevent
        // from modifying the resizeWidth or the mimetype.
        should_optimize_image_predicates: () => false,
    };

    setup() {
        this.imageTranslationsMap = new Map();
    }

    async onWillSaveMediaDialogHandlers(elements, { node }) {
        for (const toProcessEl of elements) {
            if (!toProcessEl || !toProcessEl.tagName === "IMG") {
                continue;
            }
            // TODO: this is a one-to-one "translation" of the image. We bring
            // back from the original image all the manipulations that have been
            // done: shape, resizing, filters... But if the image is different,
            // those options should also be adaptable. We should have
            // translation options to handle the new image exactly like what is
            // possible in the builder.
            const dataAttrsToCopy = ["oeTranslationState"];
            const mimetype = await getMimetypeBeforeShape(toProcessEl);
            if (await isImageSupportedForProcessing(toProcessEl, mimetype)) {
                dataAttrsToCopy.push("glFilter", "resizeWidth");
            }
            for (const dataAttr of dataAttrsToCopy) {
                if (node.dataset[dataAttr]) {
                    toProcessEl.dataset[dataAttr] = node.dataset[dataAttr];
                }
            }
        }
    }

    /**
     * Prepares and keeps track of the dirty images translations before they are
     * actually saved, so that they can be updated one last time _after_ the
     * images have been processed and saved in DB (with the right info).
     * @see updateTranslationsOnImageSaved
     *
     * @param {HTMLElement} translateEl - image element
     * @param {HTMLSpanElement} spanEl - recreated translation span
     * @param {string} attr - attribute currently processed on `translateEl`
     */
    registerImageDirtyTranslations(translateEl, spanEl, attr) {
        if (translateEl.matches(".o_modified_image_to_save") && ["src", "srcset"].includes(attr)) {
            if (this.imageTranslationsMap.has(translateEl)) {
                this.imageTranslationsMap.get(translateEl).push([attr, spanEl]);
            } else {
                this.imageTranslationsMap.set(translateEl, [[attr, spanEl]]);
            }
        }
    }
    /**
     * Updates the image translations after their final processing, just before
     * save. Typically to change src/srcset from base64 to actual URLs.
     * @see ImageSavePlugin.saveModifiedImage
     *
     * @param {Object} info
     * @param {HTMLImageElement} info.imageEl
     */
    updateTranslationsOnImageSaved({ imageEl }) {
        const fallbackAttributes = { srcset: "src" };
        if (this.imageTranslationsMap.has(imageEl)) {
            for (const [attr, spanEl] of this.imageTranslationsMap.get(imageEl)) {
                spanEl.textContent =
                    imageEl.getAttribute(attr) ||
                    imageEl.getAttribute(fallbackAttributes[attr]) ||
                    spanEl.textContent;
            }
            this.imageTranslationsMap.delete(imageEl);
        }
    }
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["domObserver", "media", "translation"];
    canTimeout = false;

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
        };
    }

    async apply({ editingElement, params: { mainParam: mediaType } }) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog(
                {
                    onlyImages: mediaType === "images",
                    noImages: mediaType !== "images",
                    visibleTabs: [mediaType.toUpperCase()],
                    node: editingElement,
                    save:
                        mediaType === "documents"
                            ? null
                            : (newMediaEl) => {
                                  this.savingMap[mediaType](editingElement, newMediaEl);
                                  editingElement.classList.add("oe_translated");
                                  this.trigger("on_media_replaced_handlers", {
                                      newMediaEl: editingElement,
                                  });
                              },
                },
                // Pass the editable to save media on the `ir.ui.view` model,
                // not on `website`, in order to upload as a public image and
                // reuse existing public images.
                this.editable
            );
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
        this.dependencies.domObserver.applyCustomMutation({
            apply: () => {
                updateTranslationMap(el, translation, attribute);
            },
            revert: () => {
                updateTranslationMap(el, originalText, attribute);
            },
        });
    }

    saveImage(editingElement, newImgEl) {
        // Replicate all attributes from the new image to the current element,
        // so that the translations are linked to the original element on save.
        const attributesToKeep = ["alt", "title"];
        for (const attr of [...editingElement.attributes]) {
            if (!attributesToKeep.includes(attr.name)) {
                editingElement.removeAttribute(attr.name);
            }
        }
        for (const attr of newImgEl.attributes) {
            if (!attributesToKeep.includes(attr.name)) {
                editingElement.setAttribute(attr.name, attr.value);
            }
        }
        const elTranslationInfo = this.dependencies.translation.getTranslationInfo(editingElement);
        const originalSrc = elTranslationInfo.src.translation;
        const originalSrcset = elTranslationInfo.srcset?.translation;
        const translatedSrc = editingElement.getAttribute("src");
        this.handleTranslationMapHistory(editingElement, translatedSrc, originalSrc, "src");
        if (originalSrcset) {
            // Hack: we don't have the new srcset yet (it's computed on save).
            // Instead, register the new src: on most images, the actual srcset
            // will be updated on save; on others (e.g. CORS-protected), it will
            // make up for the lack of actual srcset.
            this.handleTranslationMapHistory(
                editingElement,
                translatedSrc,
                originalSrcset,
                "srcset"
            );
        }
    }
}
