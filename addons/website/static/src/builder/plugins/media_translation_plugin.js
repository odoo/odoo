import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = ["translation"];

    resources = {
        builder_options: [
            {
                template: "website.ImgTranslationOption",
                selector: "img[data-oe-translatable-link]",
                isTranslationOption: true,
            },
            {
                template: "website.VideoTranslationOption",
                selector: ".media_iframe_video:has(iframe[data-oe-translatable-link])",
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
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["history", "imagePostProcess", "media", "translation"];

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
            videos: this.saveVideo.bind(this),
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
}
