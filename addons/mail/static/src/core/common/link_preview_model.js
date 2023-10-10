/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class LinkPreview extends Record {
    static id = "id";
    /** @returns {import("models").LinkPreview} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").LinkPreview}
     */
    static insert(data) {
        const message = this.store.Message.get(data.message_id);
        data.message = message;
        delete data.message_id;
        /** @type {import("models").LinkPreview} */
        const linkPreview = this.preinsert(data);
        Object.assign(linkPreview, data);
        message?.linkPreviews.add(linkPreview);
        return linkPreview;
    }

    /** @type {number} */
    id;
    message = Record.one("Message");
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


    get monthYear() {
        const message = this.message ?? this._store.Message.get(this.message_id);
        if (!message) {
            return undefined;
        }
        const datetime = deserializeDateTime(message.create_date);
        return `${datetime.monthLong}, ${datetime.year}`;
    }
}

LinkPreview.register();
