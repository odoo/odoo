/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadViewer',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @param {integer} scrollHeight
         * @param {ThreadCache} threadCache
         */
        saveThreadCacheScrollHeightAsInitial(scrollHeight, threadCache) {
            threadCache = threadCache || this.threadCache;
            if (!threadCache) {
                return;
            }
            if (this.chatter) {
                // Initial scroll height is disabled for chatter because it is
                // too complex to handle correctly and less important
                // functionally.
                return;
            }
            this.update({
                threadCacheInitialScrollHeights: Object.assign({}, this.threadCacheInitialScrollHeights, {
                    [threadCache.localId]: scrollHeight,
                }),
            });
        },
        /**
         * @param {integer} scrollTop
         * @param {ThreadCache} threadCache
         */
        saveThreadCacheScrollPositionsAsInitial(scrollTop, threadCache) {
            threadCache = threadCache || this.threadCache;
            if (!threadCache) {
                return;
            }
            if (this.chatter) {
                // Initial scroll position is disabled for chatter because it is
                // too complex to handle correctly and less important
                // functionally.
                return;
            }
            this.update({
                threadCacheInitialScrollPositions: Object.assign({}, this.threadCacheInitialScrollPositions, {
                    [threadCache.localId]: scrollTop,
                }),
            });
        },
        /**
         * @private
         * @returns {ThreadViewer|undefined}
         */
        _computeThreadView() {
            return this.hasThreadView ? insertAndReplace() : clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeThreadView_hasComposerThreadTyping() {
            if (this.discussPublicView) {
                return true;
            }
            if (this.discuss) {
                return true;
            }
            return clear();
        },
    },
    fields: {
        chatter: one('Chatter', {
            identifying: true,
            inverse: 'threadViewer',
        }),
        chatWindow: one('ChatWindow', {
            identifying: true,
            inverse: 'threadViewer',
        }),
        /**
         * true if the viewer is in a compact format, like in a chat window.
         */
        compact: attr({
            default: false,
        }),
        discuss: one('Discuss', {
            identifying: true,
            inverse: 'threadViewer',
        }),
        discussPublicView: one('DiscussPublicView', {
            identifying: true,
            inverse: 'threadViewer',
        }),
        /**
         * Determines which extra class this thread view component should have.
         */
        extraClass: attr(),
        /**
         * Determines whether this thread viewer has a member list.
         * Only makes sense if this thread is a channel and if the channel is
         * not a chat.
         */
        hasMemberList: attr({
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            default: false,
        }),
        /**
         * Determines whether this thread viewer has a top bar.
         */
        hasTopbar: attr({
            default: false,
        }),
        /**
         * Determines the order mode of the messages on this thread viewer.
         * Either 'asc', or 'desc'.
         */
        order: attr({
            default: 'asc',
        }),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         */
        thread: one('Thread'),
        /**
         * States the `ThreadCache` that should be displayed by `this`.
         */
        threadCache: one('ThreadCache', {
            related: 'thread.cache',
        }),
        /**
         * Determines the initial scroll height of thread caches, which is the
         * scroll height at the time the last scroll position was saved.
         * Useful to only restore scroll position when the corresponding height
         * is available, otherwise the restore makes no sense.
         */
        threadCacheInitialScrollHeights: attr({
            default: {},
        }),
        /**
         * Determines the initial scroll positions of thread caches.
         * Useful to restore scroll position on changing back to this
         * thread cache. Note that this is only applied when opening
         * the thread cache, because scroll position may change fast so
         * save is already throttled.
         */
        threadCacheInitialScrollPositions: attr({
            default: {},
        }),
        /**
         * States the `ThreadView` currently displayed and managed by `this`.
         */
        threadView: one('ThreadView', {
            compute: '_computeThreadView',
            inverse: 'threadViewer',
            isCausal: true,
        }),
        threadView_hasComposerThreadTyping: attr({
            compute: '_computeThreadView_hasComposerThreadTyping',
        }),
    },
});
