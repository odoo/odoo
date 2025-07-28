import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getImageSrc } from "@html_editor/utils/image";
import { getDataURLBinarySize } from "@html_editor/utils/image_processing";

const imageCacheSize = new Map();

export class ImageSize extends BaseOptionComponent {
    static template = "html_builder.ImageSize";
    static props = {};
    setup() {
        super.setup();
        this.imagePostProcess = this.env.editor.shared.imagePostProcess;
        this.state = useDomState(async (el) => ({
            size: await this.getImageSize(el),
        }));
    }
    async getImageSize(el) {
        const src = getImageSrc(el);
        if (!src) {
            return;
        }
        let size;
        if (isBase64ImageSrc(src)) {
            size = getDataURLBinarySize(src);
        } else {
            if (imageCacheSize.has(src)) {
                size = imageCacheSize.get(src);
            } else {
                size = await this.imagePostProcess.getProcessedImageSize(el);
                imageCacheSize.set(src, size);
            }
        }
        return `${(size / 1024).toFixed(1)} kB`;
    }
}
function isBase64ImageSrc(src) {
    // Check if it's a data URL with base64 encoding
    return src && src.startsWith("data:image/") && src.includes(";base64,");
}
