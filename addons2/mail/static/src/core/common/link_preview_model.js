/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class LinkPreview extends Record {
    static id = "id";
    /** @returns {import("models").LinkPreview} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").LinkPreview|import("models").LinkPreview[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    message = Record.one("Message", { inverse: "linkPreviews" });
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
        return Boolean(!this.isImage && this.og_type && this.og_type.startsWith("video"));
    }

    get isCard() {
        return !this.isImage && !this.isVideo;
    }
}

LinkPreview.register();
