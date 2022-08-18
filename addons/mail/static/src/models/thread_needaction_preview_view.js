/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { htmlToTextContentInline } from '@mail/js/utils';

registerModel({
    name: 'ThreadNeedactionPreviewView',
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
            const messaging = this.messaging;
            this.thread.open();
            if (!messaging.device.isSmall) {
                messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            this.messaging.models['Message'].markAllAsRead([
                ['model', '=', this.thread.model],
                ['res_id', '=', this.thread.id],
            ]);
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInlineLastNeedactionMessageAsOriginThreadBody() {
            if (!this.thread.lastNeedactionMessageAsOriginThread) {
                return clear();
            }
            return htmlToTextContentInline(this.thread.lastNeedactionMessageAsOriginThread.prettyBody);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsEmpty() {
            return !this.inlineLastNeedactionMessageAsOriginThreadBody && !this.lastTrackingValue;
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
                this.thread.lastNeedactionMessageAsOriginThread &&
                this.thread.lastNeedactionMessageAsOriginThread.author
            ) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.thread.correspondent && this.thread.correspondent.isImStatusSet ? {} : clear();
        },
    },
    fields: {
        inlineLastNeedactionMessageAsOriginThreadBody: attr({
            compute: '_computeInlineLastNeedactionMessageAsOriginThreadBody',
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
            inverse: 'threadNeedactionPreviewViewOwner',
            isCausal: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'threadNeedactionPreviewViews',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'threadNeedactionPreviewViewOwner',
            isCausal: true,
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'threadNeedactionPreviewViews',
        }),
    },
});
