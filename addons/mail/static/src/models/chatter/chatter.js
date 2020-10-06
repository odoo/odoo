odoo.define('mail/static/src/models/chatter/chatter.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    const getThreadNextTemporaryId = (function () {
        let tmpId = 0;
        return () => {
            tmpId -= 1;
            return tmpId;
        };
    })();

    const getMessageNextTemporaryId = (function () {
        let tmpId = 0;
        return () => {
            tmpId -= 1;
            return tmpId;
        };
    })();

    class Chatter extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            this._stopAttachmentsLoading();
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        focus() {
            this.update({ isDoFocus: true });
        }

        async refresh() {
            if (this.hasActivities) {
                this.thread.refreshActivities();
            }
            if (this.hasFollowers) {
                this.thread.refreshFollowers();
                this.thread.fetchAndUpdateSuggestedRecipients();
            }
            if (this.hasMessageList) {
                this.thread.refresh();
            }
        }

        showLogNote() {
            this.update({ isComposerVisible: true });
            this.thread.composer.update({ isLog: true });
            this.focus();
        }

        showSendMessage() {
            this.update({ isComposerVisible: true });
            this.thread.composer.update({ isLog: false });
            this.focus();
        }

        toggleActivityBoxVisibility() {
            this.update({ isActivityBoxVisible: !this.isActivityBoxVisible });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return this.thread && this.hasMessageList;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDisabled() {
            return !this.thread || this.thread.isTemporary;
        }

        /**
         * @private
         */
        _onThreadIdOrThreadModelChanged() {
            if (this.threadId) {
                if (this.thread && this.thread.isTemporary) {
                    this.thread.delete();
                }
                this.update({
                    isAttachmentBoxVisible: this.isAttachmentBoxVisibleInitially,
                    thread: [['insert', {
                        // If the thread was considered to have the activity
                        // mixin once, it will have it forever.
                        hasActivities: this.hasActivities ? true : undefined,
                        id: this.threadId,
                        model: this.threadModel,
                    }]],
                });
                if (this.hasActivities) {
                    this.thread.refreshActivities();
                }
                if (this.hasFollowers) {
                    this.thread.refreshFollowers();
                    this.thread.fetchAndUpdateSuggestedRecipients();
                }
                if (this.hasMessageList) {
                    this.thread.refresh();
                }
            } else if (!this.thread || !this.thread.isTemporary) {
                const currentPartner = this.env.messaging.currentPartner;
                const message = this.env.models['mail.message'].create({
                    author: [['link', currentPartner]],
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                const nextId = getThreadNextTemporaryId();
                this.update({
                    isAttachmentBoxVisible: false,
                    thread: [['insert', {
                        areAttachmentsLoaded: true,
                        id: nextId,
                        isTemporary: true,
                        model: this.threadModel,
                    }]],
                });
                for (const cache of this.thread.caches) {
                    cache.update({ messages: [['link', message]] });
                }
            }
        }

        /**
         * @private
         */
        _onThreadIsLoadingAttachmentsChanged() {
            if (!this.thread.isLoadingAttachments) {
                this._stopAttachmentsLoading();
                return;
            }
            if (this._isPreparingAttachmentsLoading || this.isShowingAttachmentsLoading) {
                return;
            }
            this._prepareAttachmentsLoading();
        }

        /**
         * @private
         */
        _prepareAttachmentsLoading() {
            this._isPreparingAttachmentsLoading = true;
            this._attachmentsLoaderTimeout = this.env.browser.setTimeout(() => {
                this.update({ isShowingAttachmentsLoading: true });
                this._isPreparingAttachmentsLoading = false;
            }, this.env.loadingBaseDelayDuration);
        }

        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.env.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
            this.update({ isShowingAttachmentsLoading: false });
            this._isPreparingAttachmentsLoading = false;
        }

    }

    Chatter.fields = {
        composer: many2one('mail.composer', {
            related: 'thread.composer',
        }),
        context: attr({
            default: {},
        }),
        /**
         * Determines whether `this` should display an activity box.
         */
        hasActivities: attr({
            default: true,
        }),
        hasExternalBorder: attr({
            default: true,
        }),
        /**
         * Determines whether `this` should display followers menu.
         */
        hasFollowers: attr({
            default: true,
        }),
        /**
         * Determines whether `this` should display a message list.
         */
        hasMessageList: attr({
            default: true,
        }),
        /**
         * Whether the message list should manage its scroll.
         * In particular, when the chatter is on the form view's side,
         * then the scroll is managed by the message list.
         * Also, the message list shoud not manage the scroll if it shares it
         * with the rest of the page.
         */
        hasMessageListScrollAdjust: attr({
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                'hasMessageList',
                'thread',
            ],
        }),
        hasTopbarCloseButton: attr({
            default: false,
        }),
        isActivityBoxVisible: attr({
            default: true,
        }),
        /**
         * Determiners whether the attachment box is currently visible.
         */
        isAttachmentBoxVisible: attr({
            default: false,
        }),
        /**
         * Determiners whether the attachment box is visible initially.
         */
        isAttachmentBoxVisibleInitially: attr({
            default: false,
        }),
        isComposerVisible: attr({
            default: false,
        }),
        isDisabled: attr({
            compute: '_computeIsDisabled',
            default: false,
            dependencies: [
                'threadIsTemporary',
            ],
        }),
        /**
         * Determine whether this chatter should be focused at next render.
         */
        isDoFocus: attr({
            default: false,
        }),
        isShowingAttachmentsLoading: attr({
            default: false,
        }),
        /**
         * Not a real field, used to trigger its compute method when one of the
         * dependencies changes.
         */
        onThreadIdOrThreadModelChanged: attr({
            compute: '_onThreadIdOrThreadModelChanged',
            dependencies: [
                'threadId',
                'threadModel',
            ],
        }),
        /**
         * Not a real field, used to trigger its compute method when one of the
         * dependencies changes.
         */
        onThreadIsLoadingAttachmentsChanged: attr({
            compute: '_onThreadIsLoadingAttachmentsChanged',
            dependencies: [
                'threadIsLoadingAttachments',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread'),
        /**
         * Determines the id of the thread that will be displayed by `this`.
         */
        threadId: attr(),
        /**
         * Serves as compute dependency.
         */
        threadIsLoadingAttachments: attr({
            related: 'thread.isLoadingAttachments',
        }),
        /**
         * Serves as compute dependency.
         */
        threadIsTemporary: attr({
            related: 'thread.isTemporary',
        }),
        /**
         * Determines the model of the thread that will be displayed by `this`.
         */
        threadModel: attr(),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        threadView: one2one('mail.thread_view', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: 'chatter',
            isCausal: true,
        }),
    };

    Chatter.modelName = 'mail.chatter';

    return Chatter;
}

registerNewModel('mail.chatter', factory);

});
