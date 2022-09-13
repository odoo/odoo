/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'LinkPreviewListView',
    recordMethods: {
        /**
         * @private
         * @returns {LinkPreviewCardView[]}
         */
        _computeLinkPreviewAsCardViews() {
            return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isCard).map(linkPreview => ({ linkPreview }));
        },
        /**
         * @private
         * @returns {LinkPreviewImageView[]}
         */
        _computeLinkPreviewAsImageViews() {
            return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isImage).map(linkPreview => ({ linkPreview }));
        },
        /**
         * @private
         * @returns {LinkPreviewVideoView[]}
         */
        _computeLinkPreviewAsVideoViews() {
            return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isVideo).map(linkPreview => ({ linkPreview }));
        },
    },
    fields: {
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        linkPreviewAsCardViews: many('LinkPreviewCardView', {
            compute: '_computeLinkPreviewAsCardViews',
            inverse: 'linkPreviewListViewOwner',
        }),
        linkPreviewAsImageViews: many('LinkPreviewImageView', {
            compute: '_computeLinkPreviewAsImageViews',
            inverse: 'linkPreviewListViewOwner',
        }),
        linkPreviewAsVideoViews: many('LinkPreviewVideoView', {
            compute: '_computeLinkPreviewAsVideoViews',
            inverse: 'linkPreviewListViewOwner',
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'linkPreviewListView',
        }),
    },
});
