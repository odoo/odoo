/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LinkPreviewCardView',
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
    },
    fields: {
        isHovered: attr({
            default: false,
        }),
        linkPreview: one('LinkPreview', {
            identifying: true,
            inverse: 'linkPreviewCardView',
        }),
        linkPreviewAsideView: one('LinkPreviewAsideView', {
            compute: '_computeLinkPreviewAsideView',
            inverse: 'linkPreviewCardView',
        }),
        linkPreviewListViewOwner: one('LinkPreviewListView', {
            identifying: true,
            inverse: 'linkPreviewAsCardViews',
        }),
    },
});
