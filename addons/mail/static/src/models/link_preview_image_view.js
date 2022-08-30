/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LinkPreviewImageView',
    recordMethods: {
        /**
         * Handles mouse enter event for the container of this element.
         */
        onMouseEnter() {
            this.update({ isHovered: true });
        },
        /**
         * Handles mouse leave event for the container of this element.
         */
        onMouseLeave() {
            this.update({ isHovered: false });
        },
        /**
         * @private
         * @returns {LinkPreviewAsideView|FieldCommand}
         */
        _computeLinkPreviewAsideView() {
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
        /**
         * @private
         * @returns {string}
         */
        _computeImageUrl() {
            return this.linkPreview.og_image ? this.linkPreview.og_image : this.linkPreview.source_url;
        },
    },
    fields: {
        imageUrl: attr({
            compute: '_computeImageUrl',
        }),
        isHovered: attr({
            default: false,
        }),
        linkPreview: one('LinkPreview', {
            identifying: true,
            inverse: 'linkPreviewImageView',
        }),
        linkPreviewAsideView: one('LinkPreviewAsideView', {
            compute: '_computeLinkPreviewAsideView',
            inverse: 'linkPreviewImageView',
            isCausal: true,
        }),
        linkPreviewListViewOwner: one('LinkPreviewListView', {
            identifying: true,
            inverse: 'linkPreviewAsImageViews',
        }),
    },
});
