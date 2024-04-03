/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LinkPreviewVideoView',
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
        isHovered: attr({
            default: false,
        }),
        linkPreview: one('LinkPreview', {
            identifying: true,
            inverse: 'linkPreviewVideoView',
        }),
        linkPreviewAsideView: one('LinkPreviewAsideView', {
            compute() {
                if (!this.linkPreview.isDeletable) {
                    return clear();
                }
                if (this.messaging.device.isMobileDevice) {
                    return {};
                }
                if (this.isHovered || (this.linkPreviewAsideView && this.linkPreviewAsideView.linkPreviewDeleteConfirmDialog)) {
                    return {};
                }
                return clear();
            },
            inverse: 'linkPreviewVideoView',
        }),
        linkPreviewListViewOwner: one('LinkPreviewListView', {
            identifying: true,
            inverse: 'linkPreviewAsVideoViews',
        }),
    },
});
