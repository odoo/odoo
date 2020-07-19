odoo.define('mail/static/src/models/thread_viewer/thread_viewer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ThreadViewer extends dependencies['mail.model'] {

        /**
         * @override
         */
        delete() {
            this._stopLoading();
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This function register a hint for the component related to this
         * record. Hints are information on changes around this viewer that
         * make require adjustment on the component. For instance, if this
         * thread viewer initiated a thread cache load and it now has become
         * loaded, then it may need to auto-scroll to last message.
         *
         * @param {string} hintType name of the hint. Used to determine what's
         *   the broad type of adjustement the component has to do.
         * @param {any} [hintData] data of the hint. Used to fine-tune
         *   adjustments on the component.
         */
        addComponentHint(hintType, hintData) {
            const hint = { data: hintData, type: hintType };
            this.update({
                componentHintList: this.componentHintList.concat([hint]),
            });
        }

        /**
         * @param {mail.thread_cache} threadCache
         */
        handleThreadCacheLoaded(threadCache) {
            if (threadCache !== this.threadCache) {
                return;
            }
            this._stopLoading();
        }

        /**
         * @param {Object} hint
         */
        markComponentHintProcessed(hint) {
            let filterFun;
            switch (hint.type) {
                case 'current-partner-just-posted-message':
                    filterFun = h => h.type !== hint.type && h.messageId !== hint.data.messageId;
                    break;
                default:
                    filterFun = h => h.type !== hint.type;
                    break;
            }
            this.update({
                componentHintList: this.componentHintList.filter(filterFun),
            });
        }

        /**
         * @param {mail.message} message
         */
        handleVisibleMessage(message) {
            if (!this.lastVisibleMessage || this.lastVisibleMessage.id < message.id) {
                this.update({ lastVisibleMessage: [['replace', message]] });
            }
        }

        /**
         * @param {string} scrollTop
         */
        saveThreadCacheScrollPositionsAsInitial(scrollTop) {
            if (!this.threadCache) {
                return;
            }
            this.update({
                threadCacheInitialScrollPositions: Object.assign({}, this.threadCacheInitialScrollPositions, {
                    [this.threadCache.localId]: scrollTop,
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
                return [];
            }
            return [['replace', this.thread.cache(this.stringifiedDomain)]];
        }

        /**
         * Not a real field, used to trigger `thread.markAsSeen` when one of
         * the dependencies changes.
         *
         * @private
         * @returns {boolean}
         */
        _computeThreadShouldBeSetAsSeen() {
            // FIXME condition should not be on "composer is focused" but "thread viewer is active"
            // See task-2277543
            const lastMessageIsVisible = this.lastVisibleMessage &&
                this.lastVisibleMessage === this.lastMessage;
            if (lastMessageIsVisible && this.hasComposerFocus && this.thread) {
                this.thread.markAsSeen();
            }
            return true;
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollPosition() {
            if (!this.threadCache) {
                return undefined;
            }
            return this.threadCacheInitialScrollPositions[this.threadCache.localId];
        }

        /**
         * @private
         */
        _prepareLoading() {
            this._isPreparingLoading = true;
            this._loaderTimeout = setTimeout(() => {
                this.isShowingLoading = true;
                this._isPreparingLoading = false;
            }, 400);
        }

        /**
         * @private
         */
        _stopLoading() {
            clearTimeout(this._loaderTimeout);
            this._loaderTimeout = null;
            this.isShowingLoading = false;
            this._isPreparingLoading = false;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            if (this.thread && this.thread !== previous.thread) {
                this._stopLoading();
                if (!this.threadCache.isLoaded && !this.threadCache.isLoading) {
                    this.threadCache.loadMessages();
                }
            }
            if (this.threadCache !== previous.threadCache) {
                this._stopLoading();
                this.addComponentHint('change-of-thread-cache');
            }

            if (
                this.thread && this.threadCache && this.threadCache.isLoading &&
                !this.isShowingLoading && !this._isPreparingLoading
            ) {
                this._prepareLoading();
            }
        }

        /**
         * @override
         */
        _updateBefore() {
            return {
                thread: this.thread,
                threadCache: this.threadCache,
            };
        }

    }

    ThreadViewer.fields = {
        chatWindow: one2one('mail.chat_window', {
            inverse: 'threadViewer',
        }),
        checkedMessages: many2many('mail.message', {
            related: 'threadCache.checkedMessages',
        }),
        /**
         * List of component hints. Hints contain information that help
         * components make UI/UX decisions based on their UI state.
         * For instance, on receiving new messages and the last message
         * is visible, it should auto-scroll to this new last message.
         *
         * Format of a component hint:
         *
         *   {
         *       type: {string} the name of the component hint. Useful
         *                      for components to dispatch behaviour
         *                      based on its type.
         *       data: {Object} data related to the component hint.
         *                      For instance, if hint suggests to scroll
         *                      to a certain message, data may contain
         *                      message id.
         *   }
         */
        componentHintList: attr({
            default: [],
        }),
        composer: many2one('mail.composer', {
            related: 'thread.composer',
        }),
        hasComposerFocus: attr({
            related: 'composer.hasFocus',
        }),
        lastMessage: many2one('mail.message', {
            related: 'thread.lastMessage',
        }),
        /**
         * Most recent message in the current thread viewer that has been shown
         * to the current partner.
         */
        lastVisibleMessage: many2one('mail.message'),
        messages: many2many('mail.message', {
            related: 'threadCache.messages',
        }),
        stringifiedDomain: attr({
            default: '[]',
        }),
        thread: many2one('mail.thread', {
            inverse: 'viewers',
        }),
        threadCache: many2one('mail.thread_cache', {
            compute: '_computeThreadCache',
            dependencies: [
                'stringifiedDomain',
                'thread',
                'threadCaches',
            ],
        }),
        threadCacheInitialScrollPosition: attr({
            compute: '_computeThreadCacheInitialScrollPosition',
            dependencies: [
                'threadCache',
                'threadCacheInitialScrollPositions',
            ],
        }),
        /**
         * List of saved initial scroll positions of thread caches.
         * Useful to restore scroll position on changing back to this
         * thread cache. Note that this is only applied when opening
         * the thread cache, because scroll position may change fast so
         * save is already throttled
         */
        threadCacheInitialScrollPositions: attr({
            default: {},
        }),
        threadCaches: many2many('mail.thread_cache', {
            related: 'thread.caches',
        }),
        /**
         * Not a real field, used to trigger `thread.markAsSeen` when one of
         * the dependencies changes.
         */
        threadShouldBeSetAsSeen: attr({
            compute: '_computeThreadShouldBeSetAsSeen',
            dependencies: [
                'hasComposerFocus',
                'lastMessage',
                'lastVisibleMessage',
                'threadCache',
            ],
        }),
        uncheckedMessages: many2many('mail.message', {
            related: 'threadCache.uncheckedMessages',
        }),
    };

    ThreadViewer.modelName = 'mail.thread_viewer';

    return ThreadViewer;
}

registerNewModel('mail.thread_viewer', factory);

});
