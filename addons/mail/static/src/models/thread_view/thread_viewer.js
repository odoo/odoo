odoo.define('mail/static/src/models/thread_viewer/thread_viewer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2one } = require('mail/static/src/model/model_field.js');

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
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (this.chatter) {
                return this.chatter.hasThreadView;
            }
            if (this.chatWindow) {
                return this.chatWindow.hasThreadView;
            }
            if (this.discuss) {
                return this.discuss.hasThreadView;
            }
            return this.hasThreadView;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeStringifiedDomain() {
            if (this.chatter) {
                return '[]';
            }
            if (this.chatWindow) {
                return '[]';
            }
            if (this.discuss) {
                return this.discuss.stringifiedDomain;
            }
            return this.stringifiedDomain;
        }

        /**
         * @private
         * @returns {mail.thread|undefined}
         */
         _computeThread() {
            if (this.chatter) {
                if (!this.chatter.thread) {
                    return [['unlink']];
                }
                return [['link', this.chatter.thread]];
            }
            if (this.chatWindow) {
                if (!this.chatWindow.thread) {
                    return [['unlink']];
                }
                return [['link', this.chatWindow.thread]];
            }
            if (this.discuss) {
                if (!this.discuss.thread) {
                    return [['unlink']];
                }
                return [['link', this.discuss.thread]];
            }
            return [];
        }

        /**
         * @private
         * @returns {mail.thread_cache|undefined}
         */
        _computeThreadCache() {
            if (!this.thread) {
                return [['unlink']];
            }
            return [['link', this.thread.cache(this.stringifiedDomain)]];
        }

        /**
         * @private
         * @returns {mail.thread_viewer|undefined}
         */
        _computeThreadView() {
            if (!this.hasThreadView) {
                return [['unlink']];
            }
            if (this.threadView) {
                return [];
            }
            return [['create']];
        }

    }

    ThreadViewer.fields = {
        /**
         * States the `mail.chatter` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        chatter: one2one('mail.chatter', {
            inverse: 'threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        chatterHasThreadView: attr({
            related: 'chatter.hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        chatterThread: many2one('mail.thread', {
            related: 'chatter.thread',
        }),
        /**
         * States the `mail.chat_window` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        chatWindow: one2one('mail.chat_window', {
            inverse: 'threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        chatWindowHasThreadView: attr({
            related: 'chatWindow.hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        chatWindowThread: many2one('mail.thread', {
            related: 'chatWindow.thread',
        }),
        /**
         * States the `mail.discuss` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        discuss: one2one('mail.discuss', {
            inverse: 'threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        discussHasThreadView: attr({
            related: 'discuss.hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        discussStringifiedDomain: attr({
            related: 'discuss.stringifiedDomain',
        }),
        /**
         * Serves as compute dependency.
         */
        discussThread: many2one('mail.thread', {
            related: 'discuss.thread',
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
            default: false,
            dependencies: [
                'chatterHasThreadView',
                'chatWindowHasThreadView',
                'discussHasThreadView',
            ],
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        stringifiedDomain: attr({
            compute: '_computeStringifiedDomain',
            default: '[]',
            dependencies: [
                'discussStringifiedDomain',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                'chatterThread',
                'chatWindowThread',
                'discussThread',
            ],
        }),
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

});
