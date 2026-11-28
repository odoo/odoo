import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getImageSrc, isImageCorsProtected } from "@html_editor/utils/image";
import { getDataURLBinarySize } from "@html_editor/utils/image_processing";

const imageCacheSize = new Map();

export class ImageSize extends BaseOptionComponent {
    static template = "html_builder.ImageSize";

    setup() {
        super.setup();
        this.imagePostProcess = this.env.editor.shared.imagePostProcess;
        this.state = useDomState((el) => ({ size: this.getImageSize(el) }));
    }
    getImageSize(el) {
        const src = getImageSrc(el);
        if (!src) {
            return;
        }
        if (isBase64ImageSrc(src)) {
            return formatSize(getDataURLBinarySize(src));
        }
        if (imageCacheSize.has(src)) {
            return formatSize(imageCacheSize.get(src));
        }
        // Not awaited. Computing the size loads and processes the image, and
        // the options must not wait for that.
        this.computeImageSize(el, src);
    }
    async computeImageSize(el, src) {
        try {
            if (await isImageCorsProtected(el)) {
                return;
            }
            const size = await this.imagePostProcess.getProcessedImageSize(el);
            imageCacheSize.set(src, size);
            if (this.env.getEditingElement() === el && getImageSrc(el) === src) {
                this.state.size = formatSize(size);
            }
        } catch (e) {
            if (!el.isConnected || this.env.editor.isDestroyed) {
                return;
            }
            throw e;
        }
    }
}
function formatSize(size) {
    return `${(size / 1024).toFixed(1)} kB`;
}
function isBase64ImageSrc(src) {
    // Check if it's a data URL with base64 encoding
    return src && src.startsWith("data:image/") && src.includes(";base64,");
}
