/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";

export class LinkPreview extends Record {
    /**
     * @param {Object} data
     * @returns {LinkPreview}
     */
    static insert(data) {
        const linkPreview = data.message.linkPreviews.find(
            (linkPreview) => linkPreview.id === data.id
        );
        if (linkPreview) {
            return Object.assign(linkPreview, data);
        }
        return new LinkPreview(data);
    }

    /** @type {number} */
    id;
    /** @type {Object} */
    message;
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
    source_url;

    /**
     * @param {Object} data
     * @returns {LinkPreview}
     */
    constructor(data) {
        super();
        Object.assign(this, data);
    }

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

modelRegistry.add(LinkPreview.name, LinkPreview);
