import {
    DEFAULT_IMAGE_QUALITY,
    shouldPreventGifTransformation,
} from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { loadImage, loadImageInfo } from "@html_editor/utils/image_processing";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clamp } from "@web/core/utils/numbers";

class ImageFormatOptionPlugin extends Plugin {
    static id = "imageFormatOption";
    static dependencies = ["imagePostProcess"];
    static shared = ["computeAvailableFormats"];
    resources = {
        builder_actions: this.getActions(),
        post_process_image_predicates: (image) =>
            image.dataset.formatMimetype || image.dataset.resizeWidth,
        process_new_image: withSequence(5, async (img) => {
            const newData = await loadImageInfo(img);
            const isNotGifOrSvg = !["image/gif", "image/svg+xml"].includes(newData.mimetype);
            const isCustomShape = newData.shape && newData.originalMimetype !== "image/gif";
            if (isNotGifOrSvg || isCustomShape) {
                const infos = await this.getImageInfos(img, "image");
                if (!infos) {
                    return;
                }
                img.dataset.formatMimetype = "image/webp";
                img.dataset.resizeWidth = infos.optimizedWidth;
            }
        }),
    };
    MAX_SUGGESTED_WIDTH = 1920;
    getActions() {
        return {
            setImageFormat: {
                isApplied: ({ editingElement, params: { width, mimetype, isOriginal } }) => {
                    const isOriginalUntouched =
                        (!editingElement.dataset.resizeWidth ||
                            !editingElement.dataset.formatMimetype) &&
                        isOriginal;
                    return (
                        isOriginalUntouched ||
                        (editingElement.dataset.resizeWidth === String(width) &&
                            editingElement.dataset.formatMimetype === mimetype)
                    );
                },
                load: async ({ editingElement: img, params: { width, mimetype } }) =>
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
     * @param {HTMLImageElement} img
     * @param {string} computeFrom - The source of the image, either "image" or "background".
     */
    async computeAvailableFormats(img, computeFrom) {
        const infos = await this.getImageInfos(img, computeFrom);
        if (!infos) {
            return [];
        }
        const { data, maxWidth, optimizedWidth } = infos;
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

    async getImageInfos(img, computeFrom) {
        const computeMaxDisplayWidth =
            computeFrom === "image"
                ? this.computeMaxDisplayWidth.bind(this)
                : this.computeMaxDisplayWidthBackground;

        const data = { ...img.dataset, ...(await loadImageInfo(img)) };
        if (!data.mimetypeBeforeConversion || shouldPreventGifTransformation(data)) {
            return;
        }

        const maxWidth = await this.getImageWidth(data.originalSrc, data.width);
        const optimizedWidth = Math.min(maxWidth, computeMaxDisplayWidth?.(img) || 0);
        return { data, maxWidth, optimizedWidth };
    }
    async getImageWidth(originalSrc, width) {
        const getNaturalWidth = () => loadImage(originalSrc).then((i) => i.naturalWidth);
        return width ? Math.round(width) : await getNaturalWidth();
    }

    computeMaxDisplayWidthBackground(img) {
        return 1920;
    }
    computeMaxDisplayWidth(img) {
        const window = img.ownerDocument.defaultView;
        if (!window) {
            return;
        }
        const computedStyles = window.getComputedStyle(img);
        const displayWidth = parseFloat(computedStyles.getPropertyValue("width"));
        const gutterWidth =
            parseFloat(computedStyles.getPropertyValue("--o-grid-gutter-width")) || 30;

        // For the logos we don't want to suggest a width too small.
        if (img.closest("nav")) {
            return Math.round(Math.min(displayWidth * 3, this.MAX_SUGGESTED_WIDTH));
            // If the image is in a container(-small), it might get bigger on
            // smaller screens. So we suggest the width of the current image unless
            // it is smaller than the size of the container on the md breapoint
            // (which is where our bootstrap columns fallback to full container
            // width since we only use col-lg-* in Odoo).
        } else if (img.closest(".container, .o_container_small")) {
            const mdContainerMaxWidth =
                parseFloat(computedStyles.getPropertyValue("--o-md-container-max-width")) || 720;
            const mdContainerInnerWidth = mdContainerMaxWidth - gutterWidth;
            return Math.round(clamp(displayWidth, mdContainerInnerWidth, this.MAX_SUGGESTED_WIDTH));
            // If the image is displayed in a container-fluid, it might also get
            // bigger on smaller screens. The same way, we suggest the width of the
            // current image unless it is smaller than the max size of the container
            // on the md breakpoint (which is the LG breakpoint since the container
            // fluid is full-width).
        } else if (img.closest(".container-fluid")) {
            const lgBp = parseFloat(computedStyles.getPropertyValue("--breakpoint-lg")) || 992;
            const mdContainerFluidMaxInnerWidth = lgBp - gutterWidth;
            return Math.round(
                clamp(displayWidth, mdContainerFluidMaxInnerWidth, this.MAX_SUGGESTED_WIDTH)
            );
        }
        // If it's not in a container, it's probably not going to change size
        // depending on breakpoints. We still keep a margin safety.
        return Math.round(Math.min(displayWidth * 1.5, this.MAX_SUGGESTED_WIDTH));
    }
}
registry.category("website-plugins").add(ImageFormatOptionPlugin.id, ImageFormatOptionPlugin);
