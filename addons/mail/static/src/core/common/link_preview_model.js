/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";

export class LinkPreview extends DiscussModel {
    static id = ["id"];

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
        super(data);
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

export class LinkPreviewManager extends DiscussModelManager {
    /** @type {typeof LinkPreview} */
    class;
    /** @type {Object.<number, LinkPreview>} */
    records = {};

    /**
     * @param {Object} data
     * @returns {LinkPreview}
     */
    insert(data) {
        const linkPreview = data.message.linkPreviews.find(
            (linkPreview) => linkPreview.id === data.id
        );
        if (linkPreview) {
            return Object.assign(linkPreview, data);
        }
        return new LinkPreview(data);
    }
}

discussModelRegistry.add("LinkPreview", [LinkPreview, LinkPreviewManager]);
