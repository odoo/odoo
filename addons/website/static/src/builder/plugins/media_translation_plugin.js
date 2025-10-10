import { BuilderAction } from "@html_builder/core/builder_action";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const translatableImgSelector = "img[data-oe-translatable-link]";
const translatableVideoSelector = ".media_iframe_video:has(iframe[data-oe-translatable-link])";
const translatableFileSelector = ".o_file_box:has(a[data-oe-translatable-link])";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = ["history", "imagePostProcess", "media", "translation"];
    static shared = ["translateMedia"];

    resources = {
        builder_options: [
            {
                template: "website.ImgTranslationOption",
                selector: translatableImgSelector,
                isTranslationOption: true,
            },
            {
                template: "website.VideoTranslationOption",
                selector: translatableVideoSelector,
                isTranslationOption: true,
            },
            {
                template: "website.DocumentTranslationOption",
                selector: translatableFileSelector,
                isTranslationOption: true,
            },
        ],
        builder_actions: {
            TranslateMediaSrcAction,
        },
        on_image_saved: (imgEl) => {
            if (imgEl.closest("[data-edit_translations]") && imgEl.dataset.oeTranslatableLink) {
                imgEl.dataset.oeTranslatableLink = imgEl.getAttribute("src");
                this.dependencies.translation.updateTranslationMap(
                    imgEl,
                    imgEl.dataset.oeTranslatableLink,
                    "data-oe-translatable-link"
                );
            }
        },
    };

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
            videos: this.saveVideo.bind(this),
            documents: this.saveDocument.bind(this),
        };
        const translatableMediaSelector = [
            translatableImgSelector,
            translatableVideoSelector,
            translatableFileSelector,
        ].join(", ");

        this.addDomListener(this.editable, "dblclick", async (ev) => {
            const targetEl = ev.target.closest(translatableMediaSelector);
            if (!targetEl) {
                return;
            }
            if (shouldEditableMediaBeEditable(targetEl)) {
                const mediaType = this.getMediaType(targetEl);
                await this.translateMedia(targetEl, mediaType);
            }
        });
    }

    getMediaType(el) {
        if (el.matches(translatableImgSelector)) {
            return "images";
        }
        if (el.matches(translatableVideoSelector)) {
            return "videos";
        }
        if (el.matches(translatableFileSelector)) {
            return "documents";
        }
    }

    async translateMedia(element, mediaType) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: mediaType === "images",
                noImages: mediaType !== "images",
                visibleTabs: [mediaType.toUpperCase()],

                node: element,
                save: async (newMediaEl) => {
                    await this.savingMap[mediaType](element, newMediaEl);
                    resolve();
                },
            });
            onClose.then(resolve);
        });
    }

    async saveImage(editingElement, newImgEl) {
        if (newImgEl && newImgEl.tagName === "IMG") {
            // TODO: this is a one-to-one "translation" of the image.
            // We bring back from the original image all the manipulations that
            // have been done: shape, resizing, filters... But if the image is
            // different, those options should also be adaptable. We should have
            // translation options to handle the new image exactly like what's
            // possible in the builder.
            const newDataset = {
                // Keep the original image data, especially oe-translate ones.
                ...editingElement.dataset,
                // Override with the translated image data.
                ...newImgEl.dataset,
            };
            editingElement.setAttribute("src", newImgEl.getAttribute("src"));
            const updateImageAttributes = await this.dependencies.imagePostProcess.processImage({
                img: editingElement,
                newDataset,
            });
            updateImageAttributes();
            editingElement.dataset.oeTranslatableLink = editingElement.getAttribute("src");
        }
    }

    async saveVideo(editingElement, newVideoEl) {
        if (newVideoEl && editingElement.classList.contains("media_iframe_video")) {
            const originalLink = editingElement.getAttribute("data-oe-expression");
            const newSrc = newVideoEl.querySelector("iframe").getAttribute("src");
            editingElement.setAttribute("data-oe-expression", newSrc);
            const iframeEl = editingElement.querySelector("iframe");
            iframeEl.setAttribute("src", newSrc);
            iframeEl.dataset.oeTranslatableLink = newSrc;
            // We force the replacement of the iframe because of a content
            // caching problem with Chrome: after save, the src is correct, but
            // the iframe's document still shows the previous src.
            iframeEl.replaceWith(iframeEl.cloneNode());
            editingElement.classList.add("oe_translated");
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    this.dependencies.translation.updateTranslationMap(
                        iframeEl,
                        newSrc,
                        "data-oe-translatable-link"
                    );
                    // No need to also update `data-oe-expression` in the map,
                    // as it's the same link.
                },
                revert: () => {
                    this.dependencies.translation.updateTranslationMap(
                        iframeEl,
                        originalLink,
                        "data-oe-translatable-link"
                    );
                },
            });
        }
    }

    async saveDocument(editingElement, newFileEl) {
        if (newFileEl) {
            const fileLinkEl = editingElement.querySelector("a.o_translatable_attribute");
            const newFileLinkEl = newFileEl.querySelector("a");
            const originalLink = fileLinkEl.dataset.oeTranslatableLink;
            const newLink = newFileLinkEl.getAttribute("href");
            fileLinkEl.href = newLink;
            fileLinkEl.dataset.oeTranslatableLink = newLink;
            editingElement.querySelector(".o_file_image").title =
                newFileEl.querySelector(".o_file_image").title;
            fileLinkEl.classList.add("oe_translated");
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    this.dependencies.translation.updateTranslationMap(
                        fileLinkEl,
                        newLink,
                        "data-oe-translatable-link"
                    );
                },
                revert: () => {
                    this.dependencies.translation.updateTranslationMap(
                        fileLinkEl,
                        originalLink,
                        "data-oe-translatable-link"
                    );
                },
            });
        }
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
