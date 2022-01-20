/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'MessageListView',
    identifyingFields: ['threadViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAtBottom() {
            return (
                this.scrollTop >= this.scrollHeight - this.clientHeight - this.endThreshold
            );
        },
        /***
         * @private
         * @returns {boolean}
         */
        _computeIsAtEnd() {
            if (this.threadViewOwner.order === 'asc') {
                return this.isAtBottom;
            }
            return this.isAtTop;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAtStart() {
            if (this.threadViewOwner.order === 'asc') {
                return this.isAtTop;
            }
            return this.isAtBottom;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAtTop() {
            return this.scrollTop <= this.endThreshold;
        },
        /**
         * @private
         * @returns {Owl.ref}
         */
        _computeScrollableElementRef() {
            if (
                this.threadViewOwner.threadViewer &&
                this.threadViewOwner.threadViewer.chatter &&
                this.threadViewOwner.threadViewer.chatter.scrollPanelRef
            ) {
                return this.threadViewOwner.threadViewer.chatter.scrollPanelRef;
            }
            if (this.scrollRef) {
                return this.scrollRef;
            }
        },
    },
    fields: {
        clientHeight: attr(),
        /**
         * States the OWL component of this message list view
         */
        component: attr(),
        /**
         * The margin that we use to detect that the scrollbar is a the end of
         * the threadView.
         */
        endThreshold: attr({
            default: 30,
        }),
        /**
         * States whether the message list scroll position is at the bottom
         * of the message list.
         */
        isAtBottom: attr({
            compute: '_computeIsAtBottom',
        }),
        /**
         * States whether the message list scroll position is at the end of
         * the message list. Depending of the message list order, this could be
         * the top or the bottom.
         */
        isAtEnd: attr({
            compute: '_computeIsAtEnd',
        }),
        /**
         * States whether the message list scroll position is at the start
         * of the message list. Depending of the message list order, this could
         * be the top or the bottom.
         */
        isAtStart: attr({
            compute: '_computeIsAtStart',
        }),
        /**
         * States whether the message list scroll position is at the top of
         * the message list.
         */
        isAtTop: attr({
            compute: '_computeIsAtTop',
        }),
        /**
         * States the ref to the html node of the message list.
         */
        scrollRef: attr(),
        /**
         * States the scrollable element for the message list.
         */
        scrollableElementRef: attr({
            compute: '_computeScrollableElementRef',
        }),
        scrollHeight: attr(),
        scrollTop: attr(),
        threadViewOwner: one('ThreadView', {
            inverse: 'messageListView',
            readonly: true,
            required: true,
        }),
    },
});
