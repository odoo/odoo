/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { create, insert, link, unlink } from '@mail/model/model_field_command';

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
         * @returns {mail.thread_cache|undefined}
         */
        _computeThreadCache() {
            if (!this.thread) {
                return unlink();
            }
            return insert({
                stringifiedDomain: this.stringifiedDomain,
                thread: link(this.thread),
            });
        }

        /**
         * @private
         * @returns {mail.thread_viewer|undefined}
         */
        _computeThreadView() {
            if (!this.hasThreadView) {
                return unlink();
            }
            if (this.threadView) {
                return;
            }
            return create();
        }

    }

    ThreadViewer.fields = {
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            default: false,
        }),
        /**
         * Determines the selected `mail.message`.
         */
        selectedMessage: many2one('mail.message'),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        stringifiedDomain: attr({
            default: '[]',
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread'),
        /**
         * States the `mail.thread_cache` that should be displayed by `this`.
         */
        threadCache: many2one('mail.thread_cache', {
            compute: '_computeThreadCache',
            dependencies: [
                'stringifiedDomain',
                'thread',
            ],
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
            dependencies: [
                'hasThreadView',
            ],
            inverse: 'threadViewer',
            isCausal: true,
        }),
    };

    ThreadViewer.modelName = 'mail.thread_viewer';

    return ThreadViewer;
}

registerNewModel('mail.thread_viewer', factory);
