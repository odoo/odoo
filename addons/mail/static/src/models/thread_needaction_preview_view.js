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
    },
    fields: {
        inlineLastNeedactionMessageAsOriginThreadBody: attr({
            compute() {
                if (!this.thread.lastNeedactionMessageAsOriginThread) {
                    return clear();
                }
                return htmlToTextContentInline(this.thread.lastNeedactionMessageAsOriginThread.prettyBody);
            },
            default: "",
        }),
        isEmpty: attr({
            compute() {
                return !this.inlineLastNeedactionMessageAsOriginThreadBody && !this.lastTrackingValue;
            },
        }),
        lastTrackingValue: one('TrackingValue', {
            compute() {
                if (this.thread.lastMessage && this.thread.lastMessage.lastTrackingValue) {
                    return this.thread.lastMessage.lastTrackingValue;
                }
                return clear();
            },
        }),
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        messageAuthorPrefixView: one('MessageAuthorPrefixView', {
            compute() {
                if (
                    this.thread.lastNeedactionMessageAsOriginThread &&
                    this.thread.lastNeedactionMessageAsOriginThread.author
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'threadNeedactionPreviewViewOwner',
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'threadNeedactionPreviewViews',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute() {
                if (
                    this.thread.channel &&
                    this.thread.channel.correspondent &&
                    this.thread.channel.correspondent.isImStatusSet
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'threadNeedactionPreviewViewOwner',
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'threadNeedactionPreviewViews',
        }),
    },
});
