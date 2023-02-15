/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

/**
 * Intermediary model to facilitate adding support for additional
 * models to the AttachmentViewer.
 */
Model({
    name: "AttachmentViewerViewable",
    identifyingMode: "xor",
    recordMethods: {
        download() {
            return this.attachmentOwner.download();
        },
    },
    fields: {
        attachmentOwner: one("Attachment", {
            identifying: true,
            inverse: "attachmentViewerViewable",
        }),
        defaultSource: attr({
            compute() {
                return this.attachmentOwner.defaultSource;
            },
        }),
        displayName: attr({
            compute() {
                return this.attachmentOwner.displayName;
            },
        }),
        imageUrl: attr({
            compute() {
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
        }),
        isImage: attr({
            compute() {
                return this.attachmentOwner.isImage;
            },
        }),
        isPdf: attr({
            compute() {
                return this.attachmentOwner.isPdf;
            },
        }),
        isText: attr({
            compute() {
                return this.attachmentOwner.isText;
            },
        }),
        isUrlYoutube: attr({
            compute() {
                return this.attachmentOwner.isUrlYoutube;
            },
        }),
        isVideo: attr({
            compute() {
                return this.attachmentOwner.isVideo;
            },
        }),
        isViewable: attr({
            compute() {
                return this.attachmentOwner.isViewable;
            },
        }),
        mimetype: attr({
            compute() {
                return this.attachmentOwner.mimetype;
            },
        }),
    },
});
