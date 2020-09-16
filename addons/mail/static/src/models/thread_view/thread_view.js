odoo.define('mail/static/src/models/thread_view/thread_view.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { RecordDeletedError } = require('mail/static/src/model/model_errors.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field_utils.js');

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
                __mfield_componentHintList: this.__mfield_componentHintList(this).concat([hint]),
            });
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
                __mfield_componentHintList: this.__mfield_componentHintList(this).filter(filterFun),
            });
        }

        /**
         * @param {mail.message} message
         */
        handleVisibleMessage(message) {
            if (
                !this.__mfield_lastVisibleMessage(this) ||
                this.__mfield_lastVisibleMessage(this).__mfield_id(this) < message.__mfield_id(this)
            ) {
                this.update({
                    __mfield_lastVisibleMessage: [['link', message]],
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollPosition() {
            if (!this.__mfield_threadCache(this)) {
                return clear();
            }
            const threadCacheInitialScrollPosition = this.__mfield_threadCacheInitialScrollPositions(this)[this.__mfield_threadCache(this).localId];
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
            // FIXME condition should not be on "composer is focused" but "threadView is active"
            // See task-2277543
            const lastMessageIsVisible = (
                this.__mfield_lastVisibleMessage(this) &&
                this.__mfield_lastVisibleMessage(this) === this.__mfield_lastMessage(this)
            );
            if (
                lastMessageIsVisible &&
                this.__mfield_hasComposerFocus(this) &&
                this.__mfield_thread(this)
            ) {
                this.__mfield_thread(this).markAsSeen(this.__mfield_lastMessage(this).__mfield_id(this)).catch(e => {
                    // prevent crash when executing compute during destroy
                    if (!(e instanceof RecordDeletedError)) {
                        throw e;
                    }
                });
            }
        }

        /**
         * @private
         */
        _onThreadCacheChanged() {
            this.addComponentHint('change-of-thread-cache');
        }

        /**
         * @private
         */
        _onThreadCacheIsLoadingChanged() {
            if (
                this.__mfield_threadCache(this) &&
                this.__mfield_threadCache(this).__mfield_isLoading(this)
            ) {
                if (
                    !this.__mfield_isLoading(this) &&
                    !this.__mfield_isPreparingLoading(this)
                ) {
                    this.update({
                        __mfield_isPreparingLoading: true,
                    });
                    this.async(() =>
                        new Promise(resolve => {
                            this._loaderTimeout = this.env.browser.setTimeout(resolve, 400);
                        }
                    )).then(() => {
                        const isLoading = this.__mfield_threadCache(this)
                            ? this.__mfield_threadCache(this).__mfield_isLoading(this)
                            : false;
                        this.update({
                            __mfield_isLoading: isLoading,
                            __mfield_isPreparingLoading: false,
                        });
                    });
                }
                return;
            }
            this.env.browser.clearTimeout(this._loaderTimeout);
            this.update({
                __mfield_isLoading: false,
                __mfield_isPreparingLoading: false,
            });
        }
    }

    ThreadView.fields = {
        __mfield_checkedMessages: many2many('mail.message', {
            related: '__mfield_threadCache.__mfield_checkedMessages',
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
        __mfield_componentHintList: attr({
            default: [],
        }),
        __mfield_composer: many2one('mail.composer', {
            related: '__mfield_thread.__mfield_composer',
        }),
        __mfield_hasComposerFocus: attr({
            related: '__mfield_composer.__mfield_hasFocus',
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
        __mfield_isLoading: attr({
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
        __mfield_isPreparingLoading: attr({
            default: false,
        }),
        __mfield_lastMessage: many2one('mail.message', {
            related: '__mfield_thread.__mfield_lastMessage',
        }),
        /**
         * Most recent message in this ThreadView that has been shown to the
         * current partner.
         */
        __mfield_lastVisibleMessage: many2one('mail.message'),
        __mfield_messages: many2many('mail.message', {
            related: '__mfield_threadCache.__mfield_messages',
        }),
        /**
         * Not a real field, used to trigger `_onThreadCacheChanged` when one of
         * the dependencies changes.
         */
        __mfield_onThreadCacheChanged: attr({
            compute: '_onThreadCacheChanged',
            dependencies: [
                '__mfield_threadCache'
            ],
        }),
        /**
         * Not a real field, used to trigger `_onThreadCacheIsLoadingChanged`
         * when one of the dependencies changes.
         *
         * @see `this.isLoading`
         */
        __mfield_onThreadCacheIsLoadingChanged: attr({
            compute: '_onThreadCacheIsLoadingChanged',
            dependencies: [
                '__mfield_threadCache',
                '__mfield_threadCacheIsLoading',
            ],
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        __mfield_stringifiedDomain: attr({
            related: '__mfield_threadViewer.__mfield_stringifiedDomain',
        }),
        /**
         * Determines the `mail.thread` currently displayed by `this`.
         */
        __mfield_thread: many2one('mail.thread', {
            inverse: '__mfield_threadViews',
            related: '__mfield_threadViewer.__mfield_thread',
        }),
        /**
         * States the `mail.thread_cache` currently displayed by `this`.
         */
        __mfield_threadCache: many2one('mail.thread_cache', {
            inverse: '__mfield_threadViews',
            related: '__mfield_threadViewer.__mfield_threadCache',
        }),
        __mfield_threadCacheInitialScrollPosition: attr({
            compute: '_computeThreadCacheInitialScrollPosition',
            dependencies: [
                '__mfield_threadCache',
                '__mfield_threadCacheInitialScrollPositions',
            ],
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_threadCacheIsLoading: attr({
            related: '__mfield_threadCache.__mfield_isLoading',
        }),
        /**
         * List of saved initial scroll positions of thread caches.
         */
        __mfield_threadCacheInitialScrollPositions: attr({
            default: {},
            related: '__mfield_threadViewer.__mfield_threadCacheInitialScrollPositions',
        }),
        /**
         * Not a real field, used to trigger `thread.markAsSeen` when one of
         * the dependencies changes.
         */
        __mfield_threadShouldBeSetAsSeen: attr({
            compute: '_computeThreadShouldBeSetAsSeen',
            dependencies: [
                '__mfield_hasComposerFocus',
                '__mfield_lastMessage',
                '__mfield_lastVisibleMessage',
                '__mfield_threadCache',
            ],
        }),
        /**
         * Determines the `mail.thread_viewer` currently managing `this`.
         */
        __mfield_threadViewer: one2one('mail.thread_viewer', {
            inverse: '__mfield_threadView',
        }),
        __mfield_uncheckedMessages: many2many('mail.message', {
            related: '__mfield_threadCache.__mfield_uncheckedMessages',
        }),
    };

    ThreadView.modelName = 'mail.thread_view';

    return ThreadView;
}

registerNewModel('mail.thread_view', factory);

});
