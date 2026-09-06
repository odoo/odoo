import { BuilderAction } from "@html_builder/core/builder_action";
import { getMimetypeBeforeShape } from "@html_builder/utils/image";
import { isImageSupportedForProcessing } from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } MediaTranslationShared
 * @property { MediaTranslationPlugin['translateMedia'] } translateMedia
 */

export const translateImageOptionSelector = "img.o_savable_attribute";
export const translateDocumentOptionSelector = ".o_file_box";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = [
        "domObserver",
        "history",
        "imagePostProcess",
        "media",
        "media_website",
        "translation",
    ];
    static shared = ["translateMedia"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            TranslateMediaSrcAction,
        },
        builder_options_render_context: {
            translateImageOptionSelector,
            translateDocumentOptionSelector,
        },
        on_will_save_media_dialog_handlers: withSequence(
            5,
            this.onWillSaveMediaDialogHandlers.bind(this)
        ),
        // As long as image options are not available in translation, prevent
        // from modifying the resizeWidth or the mimetype.
        should_optimize_image_predicates: () => false,
        replace_media_dialog_params_processors: (params) => {
            const newParams = this.getMediaDialogProps({ mediaEl: params.node });
            return Object.assign(params, newParams);
        },
        on_media_replaced_handlers: ({ newMediaEl }) => {
            if (newMediaEl.classList.contains("data-oe-translation-state")) {
                newMediaEl.classList.add("oe_translated");
            }
        },
    };

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
            const attrsToCopy = [
                "data-oe-translation-state",
                "alt",
                "title",
                ...node
                    .getAttributeNames()
                    .filter((n) => n.startsWith("data-translated-attribute-info-")),
            ];
            const mimetype = await getMimetypeBeforeShape(toProcessEl);
            if (await isImageSupportedForProcessing(toProcessEl, mimetype)) {
                attrsToCopy.push("data-gl-filter", "data-resize-width");
            }
            for (const attr of attrsToCopy) {
                if (node.hasAttribute(attr)) {
                    toProcessEl.setAttribute(attr, node.getAttribute(attr));
                }
            }
        }
    }

    getMediaDialogProps({ mediaEl }) {
        const mediaType = this.getMediaType(mediaEl);
        return {
            onlyImages: mediaType === "images",
            noImages: mediaType !== "images",
            visibleTabs: [mediaType.toUpperCase()],
            node: mediaEl,
        };
    }

    getMediaType(el) {
        if (el.matches(translateImageOptionSelector)) {
            return "images";
        }
        if (el.matches(translateDocumentOptionSelector)) {
            return "documents";
        }
    }

    /**
     * Opens the media dialog to translate the source of the media.
     * @param {HTMLElement} element - element that should be "translated"
     */
    async translateMedia(element) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog(
                this.getMediaDialogProps({ mediaEl: element }),
                // Pass the editable to save media on the `ir.ui.view` model,
                // not on `website`, in order to upload as a public image and
                // reuse existing public images.
                this.editable
            );
            onClose.then(resolve);
        });
    }
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

// TODO: why not use the existing action `replaceMedia`
export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["mediaTranslation"];
    canTimeout = false;

    async apply({ editingElement }) {
        await this.dependencies.mediaTranslation.translateMedia(editingElement);
    }
}
