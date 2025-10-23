import { MailLinkPreview } from "@mail/core/common/model_definitions";
import { convertToEmbedURL } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "avi", "mkv", "webm", "mpeg", "mpg", "ogv", "3gp"]);
patch(MailLinkPreview.prototype, {
    get isGif() {
        return [this.og_mimetype, this.image_mimetype].includes("image/gif");
    },
    get imageUrl() {
        return this.og_image ? this.og_image : this.source_url;
    },
    get isImage() {
        return Boolean(this.image_mimetype || this.og_mimetype === "image/gif");
    },
    get isVideo() {
        let fileExt;
        if (this.og_title) {
            fileExt = this.og_title.split(".").pop();
        }
        return (
            VIDEO_EXTENSIONS.has(fileExt) ||
            Boolean(!this.isImage && this.og_type && this.og_type.startsWith("video"))
        );
    },
    get isCard() {
        return !this.isImage && !this.isVideo;
    },
    get videoURL() {
        const { url } = convertToEmbedURL(this.source_url);
        return url;
    },
    get videoProvider() {
        const { provider } = convertToEmbedURL(this.source_url);
        return provider;
    },
});
export const LinkPreview = MailLinkPreview;
