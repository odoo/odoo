/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageListView',
    recordMethods: {
        /**
         * @returns {Element|undefined}
         */
        getScrollableElement() {
            if (this.threadViewOwner.threadViewer.chatter) {
                return this.threadViewOwner.threadViewer.chatter.scrollPanelRef.el;
            }
            return this.component.root.el;
        },
        onClickRetryLoadMoreMessages() {
            if (!this.exists() || !this.thread) {
                return;
            }
            this.thread.cache.update({ hasLoadingFailed: false });
            this.thread.cache.loadMoreMessages();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickLoadMore(ev) {
            ev.preventDefault();
            if (!this.exists() || !this.thread) {
                return;
            }
            this.thread.cache.loadMoreMessages();
        },
    },
    fields: {
        clientHeight: attr(),
        /**
         * States the OWL component of this message list view
         */
        component: attr(),
        hasScrollAdjust: attr({
            compute() {
                if (this.threadViewOwner.threadViewer.chatter) {
                    return this.threadViewOwner.threadViewer.chatter.hasMessageListScrollAdjust;
                }
                return clear();
            },
            default: true,
        }),
        /**
         * States whether the message list scroll position is at the end of
         * the message list. Depending of the message list order, this could be
         * the top or the bottom.
         */
        isAtEnd: attr({
            compute() {
                /**
                 * The margin that we use to detect that the scrollbar is a the end of
                 * the threadView.
                 */
                const endThreshold = 30;
                if (this.threadViewOwner.order === 'asc') {
                    return this.scrollTop >= this.scrollHeight - this.clientHeight - endThreshold;
                }
                return this.scrollTop <= endThreshold;
            },
        }),
        /**
         * States whether there was at least one programmatic scroll since the
         * last scroll event was handled (which is particularly async due to
         * throttled behavior).
         * Useful to avoid loading more messages or to incorrectly disabling the
         * auto-scroll feature when the scroll was not made by the user.
         */
        isLastScrollProgrammatic: attr({
            default: false,
        }),
        /**
         * States the message views used to display this thread view owner's messages.
         */
        messageListViewItems: many('MessageListViewItem', {
            compute() {
                if (!this.threadViewOwner.threadCache) {
                    return clear();
                }
                const orderedMessages = this.threadViewOwner.threadCache.orderedNonEmptyMessages;
                if (this.threadViewOwner.order === 'desc') {
                    orderedMessages.reverse();
                }
                const messageViewsData = [];
                let prevMessage;
                for (const message of orderedMessages) {
                    messageViewsData.push({
                        isSquashed: this.threadViewOwner._shouldMessageBeSquashed(prevMessage, message),
                        message,
                    });
                    prevMessage = message;
                }
                return messageViewsData;
            },
            inverse: 'messageListViewOwner',
        }),
        scrollHeight: attr(),
        scrollTop: attr(),
        thread: one('Thread', {
            related: 'threadViewOwner.thread',
        }),
        threadViewOwner: one('ThreadView', {
            identifying: true,
            inverse: 'messageListView',
        }),
    },
});
