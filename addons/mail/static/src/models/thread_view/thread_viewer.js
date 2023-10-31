/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class ThreadViewer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {integer} scrollHeight
         * @param {mail.thread_cache} threadCache
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
        }

        /**
         * @param {integer} scrollTop
         * @param {mail.thread_cache} threadCache
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
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.thread_viewer|undefined}
         */
        _computeThreadView() {
            return this.hasThreadView ? insertAndReplace() : clear();
        }

    }

    ThreadViewer.fields = {
        chatter: one2one('mail.chatter', {
            inverse: 'threadViewer',
            readonly: true,
        }),
        chatWindow: one2one('mail.chat_window', {
            inverse: 'threadViewer',
            readonly: true,
        }),
        /**
         * true if the viewer is in a compact format, like in a chat window.
         */
        compact: attr({
            default: false,
        }),
        discuss: one2one('mail.discuss', {
            inverse: 'threadViewer',
            readonly: true,
        }),
        discussPublicView: one2one('mail.discuss_public_view', {
            inverse: 'threadViewer',
            readonly: true,
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
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread'),
        /**
         * States the `mail.thread_cache` that should be displayed by `this`.
         */
        threadCache: many2one('mail.thread_cache', {
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
         * States the `mail.thread_view` currently displayed and managed by `this`.
         */
        threadView: one2one('mail.thread_view', {
            compute: '_computeThreadView',
            inverse: 'threadViewer',
            isCausal: true,
        }),
    };
    ThreadViewer.identifyingFields = [['chatter', 'chatWindow', 'discuss', 'discussPublicView']];
    ThreadViewer.modelName = 'mail.thread_viewer';

    return ThreadViewer;
}

registerNewModel('mail.thread_viewer', factory);
