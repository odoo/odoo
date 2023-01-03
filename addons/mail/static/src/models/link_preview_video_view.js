/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "LinkPreviewVideoView",
    template: "mail.LinkPreviewVideoView",
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
        isHovered: attr({ default: false }),
        linkPreview: one("LinkPreview", { identifying: true, inverse: "linkPreviewVideoView" }),
        linkPreviewAsideView: one("LinkPreviewAsideView", {
            inverse: "linkPreviewVideoView",
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
            inverse: "linkPreviewAsVideoViews",
        }),
    },
});
