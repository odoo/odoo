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
    static dependencies = ["imagePostProcess", "media"];

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
}
