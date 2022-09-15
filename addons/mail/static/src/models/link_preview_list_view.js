/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'LinkPreviewListView',
    fields: {
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        linkPreviewAsCardViews: many('LinkPreviewCardView', {
            compute() {
                return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isCard).map(linkPreview => ({ linkPreview }));
            },
            inverse: 'linkPreviewListViewOwner',
        }),
        linkPreviewAsImageViews: many('LinkPreviewImageView', {
            compute() {
                return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isImage).map(linkPreview => ({ linkPreview }));
            },
            inverse: 'linkPreviewListViewOwner',
        }),
        linkPreviewAsVideoViews: many('LinkPreviewVideoView', {
            compute() {
                return this.messageViewOwner.message.linkPreviews.filter(linkPreview => linkPreview.isVideo).map(linkPreview => ({ linkPreview }));
            },
            inverse: 'linkPreviewListViewOwner',
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'linkPreviewListView',
        }),
    },
});
