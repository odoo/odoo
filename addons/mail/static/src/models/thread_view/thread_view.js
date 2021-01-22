odoo.define('mail/static/src/models/thread_view/thread_view.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { RecordDeletedError } = require('mail/static/src/model/model_errors.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {

    class ThreadView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            this.env.browser.clearTimeout(this._loaderTimeout);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This function register a hint for the component related to this
         * record. Hints are information on changes around this viewer that
         * make require adjustment on the component. For instance, if this
         * ThreadView initiated a thread cache load and it now has become
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
         * @param {Object} hint
         */
        markComponentHintProcessed(hint) {
            this.update({
                componentHintList: this.componentHintList.filter(h => h !== hint),
            });
            this.env.messagingBus.trigger('o-thread-view-hint-processed', {
                hint,
                threadViewer: this.threadViewer,
            });
        }

        /**
         * @param {mail.message} message
         */
        handleVisibleMessage(message) {
            if (!this.lastVisibleMessage || this.lastVisibleMessage.id < message.id) {
                this.update({ lastVisibleMessage: [['link', message]] });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollHeight() {
            if (!this.threadCache) {
                return clear();
            }
            const threadCacheInitialScrollHeight = this.threadCacheInitialScrollHeights[this.threadCache.localId];
            if (threadCacheInitialScrollHeight !== undefined) {
                return threadCacheInitialScrollHeight;
            }
            return clear();
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollPosition() {
            if (!this.threadCache) {
                return clear();
            }
            const threadCacheInitialScrollPosition = this.threadCacheInitialScrollPositions[this.threadCache.localId];
            if (threadCacheInitialScrollPosition !== undefined) {
                return threadCacheInitialScrollPosition;
            }
            return clear();
        }

        /**
         * Not a real field, used to trigger `thread.markAsSeen` when one of
         * the dependencies changes.
         *
         * @private
         * @returns {boolean}
         */
        _computeThreadShouldBeSetAsSeen() {
            if (!this.thread) {
                return;
            }
            if (!this.thread.lastNonTransientMessage) {
                return;
            }
            if (!this.lastVisibleMessage) {
                return;
            }
            if (this.lastVisibleMessage !== this.lastMessage) {
                return;
            }
            if (!this.hasComposerFocus) {
                // FIXME condition should not be on "composer is focused" but "threadView is active"
                // See task-2277543
                return;
            }
            this.thread.markAsSeen(this.thread.lastNonTransientMessage).catch(e => {
                // prevent crash when executing compute during destroy
                if (!(e instanceof RecordDeletedError)) {
                    throw e;
                }
            });
        }

        /**
         * @private
         */
        _onThreadCacheChanged() {
            // clear obsolete hints
            this.update({ componentHintList: clear() });
            this.addComponentHint('change-of-thread-cache');
            if (this.threadCache) {
                this.threadCache.update({
                    isCacheRefreshRequested: true,
                    isMarkAllAsReadRequested: true,
                });
            }
            this.update({ lastVisibleMessage: [['unlink']] });
        }

        /**
         * @private
         */
        _onThreadCacheIsLoadingChanged() {
            if (this.threadCache && this.threadCache.isLoading) {
                if (!this.isLoading && !this.isPreparingLoading) {
                    this.update({ isPreparingLoading: true });
                    this.async(() =>
                        new Promise(resolve => {
                            this._loaderTimeout = this.env.browser.setTimeout(resolve, 400);
                        }
                    )).then(() => {
                        const isLoading = this.threadCache
                            ? this.threadCache.isLoading
                            : false;
                        this.update({ isLoading, isPreparingLoading: false });
                    });
                }
                return;
            }
            this.env.browser.clearTimeout(this._loaderTimeout);
            this.update({ isLoading: false, isPreparingLoading: false });
        }
    }

    ThreadView.fields = {
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
        /**
         * States whether `this.threadCache` is currently loading messages.
         *
         * This field is related to `this.threadCache.isLoading` but with a
         * delay on its update to avoid flickering on the UI.
         *
         * It is computed through `_onThreadCacheIsLoadingChanged` and it should
         * otherwise be considered read-only.
         */
        isLoading: attr({
            default: false,
        }),
        /**
         * States whether `this` is aware of `this.threadCache` currently
         * loading messages, but `this` is not yet ready to display that loading
         * on the UI.
         *
         * This field is computed through `_onThreadCacheIsLoadingChanged` and
         * it should otherwise be considered read-only.
         *
         * @see `this.isLoading`
         */
        isPreparingLoading: attr({
            default: false,
        }),
        /**
         * Determines whether `this` should automatically scroll on receiving
         * a new message. Detection of new message is done through the component
         * hint `message-received`.
         */
        hasAutoScrollOnMessageReceived: attr({
            default: true,
        }),
        /**
         * Last message in the context of the currently displayed thread cache.
         */
        lastMessage: many2one('mail.message', {
            related: 'thread.lastMessage',
        }),
        /**
         * Serves as compute dependency.
         */
        lastNonTransientMessage: many2one('mail.message', {
            related: 'thread.lastNonTransientMessage',
        }),
        /**
         * Most recent message in this ThreadView that has been shown to the
         * current partner in the currently displayed thread cache.
         */
        lastVisibleMessage: many2one('mail.message'),
        messages: many2many('mail.message', {
            related: 'threadCache.messages',
        }),
        nonEmptyMessages: many2many('mail.message', {
            related: 'threadCache.nonEmptyMessages',
        }),
        /**
         * Not a real field, used to trigger `_onThreadCacheChanged` when one of
         * the dependencies changes.
         */
        onThreadCacheChanged: attr({
            compute: '_onThreadCacheChanged',
            dependencies: [
                'threadCache'
            ],
        }),
        /**
         * Not a real field, used to trigger `_onThreadCacheIsLoadingChanged`
         * when one of the dependencies changes.
         *
         * @see `this.isLoading`
         */
        onThreadCacheIsLoadingChanged: attr({
            compute: '_onThreadCacheIsLoadingChanged',
            dependencies: [
                'threadCache',
                'threadCacheIsLoading',
            ],
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        stringifiedDomain: attr({
            related: 'threadViewer.stringifiedDomain',
        }),
        /**
         * Determines the `mail.thread` currently displayed by `this`.
         */
        thread: many2one('mail.thread', {
            inverse: 'threadViews',
            related: 'threadViewer.thread',
        }),
        /**
         * States the `mail.thread_cache` currently displayed by `this`.
         */
        threadCache: many2one('mail.thread_cache', {
            inverse: 'threadViews',
            related: 'threadViewer.threadCache',
        }),
        threadCacheInitialScrollHeight: attr({
            compute: '_computeThreadCacheInitialScrollHeight',
            dependencies: [
                'threadCache',
                'threadCacheInitialScrollHeights',
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
         * Serves as compute dependency.
         */
        threadCacheIsLoading: attr({
            related: 'threadCache.isLoading',
        }),
        /**
         * List of saved initial scroll heights of thread caches.
         */
        threadCacheInitialScrollHeights: attr({
            default: {},
            related: 'threadViewer.threadCacheInitialScrollHeights',
        }),
        /**
         * List of saved initial scroll positions of thread caches.
         */
        threadCacheInitialScrollPositions: attr({
            default: {},
            related: 'threadViewer.threadCacheInitialScrollPositions',
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
                'lastNonTransientMessage',
                'lastVisibleMessage',
                'threadCache',
            ],
        }),
        /**
         * Determines the `mail.thread_viewer` currently managing `this`.
         */
        threadViewer: one2one('mail.thread_viewer', {
            inverse: 'threadView',
        }),
        uncheckedMessages: many2many('mail.message', {
            related: 'threadCache.uncheckedMessages',
        }),
    };

    ThreadView.modelName = 'mail.thread_view';

    return ThreadView;
}

registerNewModel('mail.thread_view', factory);

});
