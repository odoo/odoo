import { BuilderAction } from "@html_builder/core/builder_action";
import {
    DEFAULT_IMAGE_QUALITY,
    shouldPreventGifTransformation,
} from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { loadImage, loadImageInfo } from "@html_editor/utils/image_processing";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { selectElements } from "@html_editor/utils/dom_traversal";

class ImageFormatOptionPlugin extends Plugin {
    static id = "imageFormatOption";
    static shared = ["computeAvailableFormats"];
    resources = {
        builder_actions: {
            SetImageFormatAction,
            SetImageQualityAction,
        },
        on_snippet_dropped_handlers: async ({ snippetEl }) => {
            for (const imgEl of selectElements(
                snippetEl,
                "img:not([data-mimetype]), .oe_img_bg:not([data-mimetype])"
            )) {
                const info = await loadImageInfo(imgEl);
                imgEl.dataset.mimetype = info.mimetypeBeforeConversion;
            }
        },
    };
    /**
     * Returns a list of valid formats for a given image or an empty list if
     * there is no mimetypeBeforeConversion data attribute on the image.
     */
    async computeAvailableFormats(img, computeMaxDisplayWidth) {
        const data = { ...img.dataset, ...(await loadImageInfo(img)) };
        if (!data.mimetypeBeforeConversion || shouldPreventGifTransformation(data)) {
            return [];
        }

        const maxWidth = await this.getImageWidth(data.originalSrc, data.width);
        const optimizedWidth = Math.min(maxWidth, computeMaxDisplayWidth?.(img) || 0);
        const widths = {
            128: ["128px", "image/webp"],
            256: ["256px", "image/webp"],
            512: ["512px", "image/webp"],
            1024: ["1024px", "image/webp"],
            1920: ["1920px", "image/webp"],
        };
        widths[img.naturalWidth] = [_t("%spx", img.naturalWidth), "image/webp"];
        widths[optimizedWidth] = [_t("%spx (Suggested)", optimizedWidth), "image/webp"];
        const mimetypeBeforeConversion = data.mimetypeBeforeConversion;
        widths[maxWidth] = [_t("%spx (Original)", maxWidth), mimetypeBeforeConversion, true];
        if (mimetypeBeforeConversion !== "image/webp") {
            // Avoid a key collision by subtracting 0.1 - putting the webp
            // above the original format one of the same size.
            widths[maxWidth - 0.1] = [_t("%spx", maxWidth), "image/webp"];
        }
        return Object.entries(widths)
            .filter(([width]) => width <= maxWidth)
            .sort(([v1], [v2]) => v1 - v2)
            .map(([width, [label, mimetype, isOriginal]]) => {
                const id = `${width}-${mimetype}`;
                return { id, width: Math.round(width), label, mimetype, isOriginal };
            });
    }
    async getImageWidth(originalSrc, width) {
        const getNaturalWidth = () => loadImage(originalSrc).then((i) => i.naturalWidth);
        return width ? Math.round(width) : await getNaturalWidth();
    }
}

export class SetImageFormatAction extends BuilderAction {
    static id = "setImageFormat";
    static dependencies = ["imagePostProcess"];
    isApplied({ editingElement, params: { width, mimetype, isOriginal } }) {
        const isOriginalUntouched =
            (!editingElement.dataset.resizeWidth || !editingElement.dataset.formatMimetype) &&
            isOriginal;
        return (
            isOriginalUntouched ||
            (editingElement.dataset.resizeWidth === String(width) &&
                editingElement.dataset.formatMimetype === mimetype)
        );
    }
    async load({ editingElement: img, params: { width, mimetype } }) {
        return this.dependencies.imagePostProcess.processImage({
            img,
            newDataset: {
                resizeWidth: width,
                formatMimetype: mimetype,
            },
        });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes();
    }
}
export class SetImageQualityAction extends BuilderAction {
    static id = "setImageQuality";
    static dependencies = ["imagePostProcess"];
    getValue({ editingElement: img }) {
        return ("quality" in img.dataset && img.dataset.quality) || DEFAULT_IMAGE_QUALITY;
    }
    async load({ editingElement: img, value: quality }) {
        return this.dependencies.imagePostProcess.processImage({
            img,
            newDataset: {
                quality,
            },
        });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes();
    }
}

registry.category("builder-plugins").add(ImageFormatOptionPlugin.id, ImageFormatOptionPlugin);
