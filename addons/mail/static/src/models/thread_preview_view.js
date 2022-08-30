/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { htmlToTextContentInline } from '@mail/js/utils';

registerModel({
    name: 'ThreadPreviewView',
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
            this.thread.open();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            if (this.thread.lastNonTransientMessage) {
                this.thread.markAsSeen(this.thread.lastNonTransientMessage);
            }
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInlineLastMessageBody() {
            if (!this.thread.lastMessage) {
                return clear();
            }
            return htmlToTextContentInline(this.thread.lastMessage.prettyBody);
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
            if (this.thread.lastMessage && this.thread.lastMessage.lastTrackingValue) {
                return this.thread.lastMessage.lastTrackingValue;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageAuthorPrefixView() {
            if (
                this.thread.lastMessage &&
                this.thread.lastMessage.author
            ) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {Object|FieldCommand}
         */
        _computePersonaImStatusIconView() {
            if (!this.thread.channel.correspondent) {
                return clear();
            }
            if (this.thread.channel.correspondent.isImStatusSet) {
                return {};
            }
            return clear();
        },
    },
    fields: {
        inlineLastMessageBody: attr({
            compute: '_computeInlineLastMessageBody',
            default: "",
        }),
        isEmpty: attr({
            compute: '_computeIsEmpty',
        }),
        lastTrackingValue: one('TrackingValue', {
            compute: '_computeLastTrackingValue',
        }),
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        messageAuthorPrefixView: one('MessageAuthorPrefixView', {
            compute: '_computeMessageAuthorPrefixView',
            inverse: 'threadPreviewViewOwner',
            isCausal: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'threadPreviewViews',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'threadPreviewViewOwner',
            isCausal: true,
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'threadPreviewViews',
        }),
    },
});
