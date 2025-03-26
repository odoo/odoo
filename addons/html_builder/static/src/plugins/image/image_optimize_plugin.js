import { DEFAULT_IMAGE_QUALITY } from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { loadImage } from "@html_editor/utils/image_processing";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class ImageOptimizePlugin extends Plugin {
    static id = "imageOptimize";
    static dependencies = ["imagePostProcess"];
    static shared = ["computeAvailableFormats"];
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            setImageFormat: {
                isApplied: ({ editingElement, param: { width, mimetype } }) =>
                    editingElement.dataset.resizeWidth === String(width) &&
                    editingElement.dataset.formatMimetype === mimetype,
                load: async ({ editingElement: img, param: { width, mimetype } }) =>
                    this.dependencies.imagePostProcess.processImage(img, {
                        resizeWidth: width,
                        formatMimetype: mimetype,
                    }),
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            setImageQuality: {
                getValue: ({ editingElement: img }) =>
                    ("quality" in img.dataset && img.dataset.quality) || DEFAULT_IMAGE_QUALITY,
                load: async ({ editingElement: img, value: quality }) =>
                    this.dependencies.imagePostProcess.processImage(img, {
                        quality,
                    }),
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
        };
    }
    /**
     * Returns a list of valid formats for a given image or an empty list if
     * there is no mimetypeBeforeConversion data attribute on the image.
     *
     * @private
     */
    async computeAvailableFormats(img, computeMaxDisplayWidth) {
        if (!img.dataset.mimetypeBeforeConversion) {
            return [];
        }

        const maxWidth = await this.getImageWidth(img);
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
        const mimetypeBeforeConversion = img.dataset.mimetypeBeforeConversion;
        widths[maxWidth] = [_t("%spx (Original)", maxWidth), mimetypeBeforeConversion];
        if (mimetypeBeforeConversion !== "image/webp") {
            // Avoid a key collision by subtracting 0.1 - putting the webp
            // above the original format one of the same size.
            widths[maxWidth - 0.1] = [_t("%spx", maxWidth), "image/webp"];
        }
        return Object.entries(widths)
            .filter(([width]) => width <= maxWidth)
            .sort(([v1], [v2]) => v1 - v2)
            .map(([width, [label, mimetype]]) => {
                const id = `${width}-${mimetype}`;
                return { id, width: Math.round(width), label, mimetype };
            });
    }
    async getImageWidth(img) {
        const getNaturalWidth = () =>
            loadImage(img.dataset.originalSrc).then((i) => i.naturalWidth);
        return img.dataset.width ? img.naturalWidth : await getNaturalWidth();
    }
}
registry.category("website-plugins").add(ImageOptimizePlugin.id, ImageOptimizePlugin);
