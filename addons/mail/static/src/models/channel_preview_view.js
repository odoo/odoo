/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { htmlToTextContentInline } from '@mail/js/utils';

registerModel({
    name: 'ChannelPreviewView',
    identifyingFields: ['notificationListViewOwner', 'channel'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            const markAsRead = this.markAsReadRef.el;
            if (markAsRead && markAsRead.contains(ev.target)) {
                // handled in `_onClickMarkAsRead`
                return;
            }
            this.channel.thread.open();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            if (this.channel.thread.lastNonTransientMessage) {
                this.channel.thread.markAsSeen(this.channel.thread.lastNonTransientMessage);
            }
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeImageUrl() {
            if (this.channel.correspondent) {
                return this.channel.correspondent.avatarUrl;
            }
            return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.channel.avatarCacheKey}`;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInlineLastMessageBody() {
            if (!this.channel.thread.lastMessage) {
                return clear();
            }
            return htmlToTextContentInline(this.channel.thread.lastMessage.prettyBody);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsEmpty() {
            return !this.inlineLastMessageBody && !this.lastTrackingValue;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLastTrackingValue() {
            if (this.channel.thread.lastMessage && this.channel.thread.lastMessage.lastTrackingValue) {
                return replace(this.channel.thread.lastMessage.lastTrackingValue);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageAuthorPrefixView() {
            if (
                this.channel.thread.lastMessage &&
                this.channel.thread.lastMessage.author
            ) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.channel.correspondent && this.channel.correspondent.isImStatusSet ? insertAndReplace() : clear();
        },
    },
    fields: {
        channel: one('Channel', {
            inverse: 'channelPreviewViews',
            readonly: true,
            required: true,
        }),
        imageUrl: attr({
            compute: '_computeImageUrl',
            default: '/mail/static/src/img/smiley/avatar.jpg',
        }),
        inlineLastMessageBody: attr({
            compute: '_computeInlineLastMessageBody',
            default: "",
            readonly: true,
        }),
        isEmpty: attr({
            compute: '_computeIsEmpty',
            readonly: true,
        }),
        lastTrackingValue: one('TrackingValue', {
            compute: '_computeLastTrackingValue',
            readonly: true,
        }),
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        messageAuthorPrefixView: one('MessageAuthorPrefixView', {
            compute: '_computeMessageAuthorPrefixView',
            inverse: 'channelPreviewViewOwner',
            isCausal: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'channelPreviewViews',
            readonly: true,
            required: true,
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'channelPreviewViewOwner',
            isCausal: true,
            readonly: true,
        }),
    },
});
