/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "LinkPreviewImageView",
    template: "mail.LinkPreviewImageView",
    recordMethods: {
        /**
         * Handles mouse enter event for the container of this element.
         */
        onMouseEnter() {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: true });
        },
        /**
         * Handles mouse leave event for the container of this element.
         */
        onMouseLeave() {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: false });
        },
    },
    fields: {
        imageUrl: attr({
            compute() {
                return this.linkPreview.og_image
                    ? this.linkPreview.og_image
                    : this.linkPreview.source_url;
            },
        }),
        isHovered: attr({ default: false }),
        linkPreview: one("LinkPreview", { identifying: true, inverse: "linkPreviewImageView" }),
        linkPreviewAsideView: one("LinkPreviewAsideView", {
            inverse: "linkPreviewImageView",
            compute() {
                if (!this.linkPreview.isDeletable) {
                    return clear();
                }
                if (this.messaging.device.isMobileDevice) {
                    return {};
                }
                if (
                    this.isHovered ||
                    (this.linkPreviewAsideView &&
                        this.linkPreviewAsideView.linkPreviewDeleteConfirmDialog)
                ) {
                    return {};
                }
                return clear();
            },
        }),
        linkPreviewListViewOwner: one("LinkPreviewListView", {
            identifying: true,
            inverse: "linkPreviewAsImageViews",
        }),
    },
});
