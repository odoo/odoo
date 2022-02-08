/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'MessageListView',
    identifyingFields: ['threadViewOwner'],
    recordMethods: {
        /***
         * @private
         * @returns {boolean}
         */
        _computeIsAtEnd() {
            /**
             * The margin that we use to detect that the scrollbar is a the end of
             * the threadView.
             */
            const endThreshold = 30;
            if (this.threadViewOwner.order === 'asc') {
                return this.scrollTop >= this.scrollHeight - this.clientHeight - endThreshold;
            }
            return this.scrollTop <= endThreshold;;
        },
    },
    fields: {
        clientHeight: attr(),
        /**
         * States the OWL component of this message list view
         */
        component: attr(),
        /**
         * States whether the message list scroll position is at the end of
         * the message list. Depending of the message list order, this could be
         * the top or the bottom.
         */
        isAtEnd: attr({
            compute: '_computeIsAtEnd',
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
        scrollHeight: attr(),
        scrollTop: attr(),
        threadViewOwner: one('ThreadView', {
            inverse: 'messageListView',
            readonly: true,
            required: true,
        }),
    },
});
