/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";

/**
 * Intermediary model to facilitate adding support for additional
 * models to the AttachmentViewer.
 */

registerModel({
    name: "AttachmentViewerViewable",
    identifyingMode: 'xor',
    recordMethods: {
        download() {
            return this.attachmentOwner.download();
        },
        /**
         * @private
         */
        _computeAccessToken() {
            return this.attachmentOwner.accessToken;
        },
        /**
         * @private
         */
        _computeDefaultSource() {
            return this.attachmentOwner.defaultSource;
        },
        /**
         * @private
         */
        _computeDisplayName() {
            return this.attachmentOwner.displayName;
        },
        /**
         * @private
         */
        _computeImageUrl() {
            if (
                !this.attachmentOwner.accessToken &&
                this.attachmentOwner.originThread &&
                this.attachmentOwner.originThread.model === "mail.channel"
            ) {
                return `/mail/channel/${this.attachmentOwner.originThread.id}/image/${this.attachmentOwner.id}`;
            }
            const accessToken = this.attachmentOwner.accessToken
                ? `?access_token=${this.attachmentOwner.accessToken}`
                : "";
            return `/web/image/${this.attachmentOwner.id}${accessToken}`;
        },
        /**
         * @private
         */
        _computeIsImage() {
            return this.attachmentOwner.isImage;
        },
        /**
         * @private
         */
        _computeIsPdf() {
            return this.attachmentOwner.isPdf;
        },
        /**
         * @private
         */
        _computeIsText() {
            return this.attachmentOwner.isText;
        },
        /**
         * @private
         */
        _computeIsUrlYoutube() {
            return this.attachmentOwner.isUrlYoutube;
        },
        /**
         * @private
         */
        _computeIsVideo() {
            return this.attachmentOwner.isVideo;
        },
        /**
         * @private
         */
        _computeIsViewable() {
            return this.attachmentOwner.isViewable;
        },
        /**
         * @private
         */
        _computeMimetype() {
            return this.attachmentOwner.mimetype;
        },
    },
    fields: {
        attachmentOwner: one("Attachment", {
            identifying: true,
            inverse: 'attachmentViewerViewable',
        }),
        accessToken: attr({
            compute: "_computeAccessToken",
        }),
        defaultSource: attr({
            compute: "_computeDefaultSource",
        }),
        displayName: attr({
            compute: "_computeDisplayName",
        }),
        imageUrl: attr({
            compute: "_computeImageUrl",
        }),
        isImage: attr({
            compute: "_computeIsImage",
        }),
        isPdf: attr({
            compute: "_computeIsPdf",
        }),
        isText: attr({
            compute: "_computeIsText",
        }),
        isUrlYoutube: attr({
            compute: "_computeIsUrlYoutube",
        }),
        isVideo: attr({
            compute: "_computeIsVideo",
        }),
        isViewable: attr({
            compute: "_computeIsViewable",
        }),
        mimetype: attr({
            compute: "_computeMimetype",
        }),
    },
});
