import { Record } from "@mail/core/common/record";
import { convertToEmbedURL } from "@mail/utils/common/misc";

const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "avi", "mkv", "webm", "mpeg", "mpg", "ogv", "3gp"]);

export class LinkPreview extends Record {
    static _name = "mail.link.preview";
    static id = "id";
    /** @returns {import("models").LinkPreview} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").LinkPreview[] : import("models").LinkPreview}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    message = Record.one("mail.message", { inverse: "linkPreviews" });
    /** @type {string} */
    image_mimetype;
    /** @type {string} */
    og_description;
    /** @type {string} */
    og_image;
    /** @type {string} */
    og_mimetype;
    /** @type {string} */
    og_title;
    /** @type {string} */
    og_type;
    /** @type {string} */
    og_site_name;
    /** @type {string} */
    source_url;

    get imageUrl() {
        return this.og_image ? this.og_image : this.source_url;
    }

    get isImage() {
        return Boolean(this.image_mimetype || this.og_mimetype === "image/gif");
    }

    get isVideo() {
        let fileExt;
        if (this.og_title) {
            fileExt = this.og_title.split(".").pop();
        }
        return (
            VIDEO_EXTENSIONS.has(fileExt) ||
            Boolean(!this.isImage && this.og_type && this.og_type.startsWith("video"))
        );
    }

    get isCard() {
        return !this.isImage && !this.isVideo;
    }

    get videoURL() {
        const { url } = convertToEmbedURL(this.source_url);
        return url;
    }

    get videoProvider() {
        const { provider } = convertToEmbedURL(this.source_url);
        return provider;
    }
}

LinkPreview.register();
