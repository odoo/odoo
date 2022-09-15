/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LinkPreview',
    recordMethods: {
        async remove() {
            await this.messaging.rpc({
                route: '/mail/link_preview/delete',
                params: { link_preview_id: this.id },
            }, { shadow: true });
        },
    },
    fields: {
        id: attr({
            identifying: true,
        }),
        image_mimetype: attr(),
        isCard: attr({
            compute() {
                return !this.isVideo && !this.isImage;
            },
        }),
        isDeletable: attr({
            compute() {
                if (!this.message) {
                    return false;
                }
                return (
                    (this.message.author && this.message.author === this.messaging.currentPartner) ||
                    (this.message.guestAuthor && this.message.guestAuthor === this.messaging.currentGuest)
                );
            },
        }),
        isImage: attr({
            compute() {
                return Boolean(this.image_mimetype || this.og_mimetype === 'image/gif');
            },
        }),
        isVideo: attr({
            compute() {
                if (!this.og_type) {
                    return clear();
                }
                return this.og_type.startsWith('video') && !this.isImage;
            },
        }),
        linkPreviewCardView: many('LinkPreviewCardView', {
            inverse: 'linkPreview',
        }),
        linkPreviewImageView: many('LinkPreviewImageView', {
            inverse: 'linkPreview',
        }),
        linkPreviewVideoView: many('LinkPreviewVideoView', {
            inverse: 'linkPreview',
        }),
        message: one('Message', {
            inverse: 'linkPreviews',
        }),
        og_description: attr(),
        og_image: attr(),
        og_mimetype: attr(),
        og_title: attr(),
        og_type: attr(),
        source_url: attr(),
    },
});
