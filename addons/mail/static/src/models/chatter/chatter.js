/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { create, insert, link, unlink, update } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

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
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickActivityBoxTitle = this.onClickActivityBoxTitle.bind(this);
        }

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

        /**
         * Handles click on activity box title.
         */
        onClickActivityBoxTitle() {
            this.update({ isActivityBoxVisible: !this.isActivityBoxVisible });
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
         * @returns {mail.thread_viewer}
         */
        _computeThreadViewer() {
            const threadViewerData = {
                hasThreadView: this.hasThreadView,
                thread: this.thread ? link(this.thread) : unlink(),
            };
            if (!this.threadViewer) {
                return create(threadViewerData);
            }
            return update(threadViewerData);
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
                    thread: insert({
                        // If the thread was considered to have the activity
                        // mixin once, it will have it forever.
                        hasActivities: this.hasActivities ? true : undefined,
                        id: this.threadId,
                        model: this.threadModel,
                    }),
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
                const currentPartner = this.messaging.currentPartner;
                const message = this.messaging.models['mail.message'].create({
                    author: link(currentPartner),
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                const nextId = getThreadNextTemporaryId();
                this.update({
                    isAttachmentBoxVisible: false,
                    thread: insert({
                        areAttachmentsLoaded: true,
                        id: nextId,
                        isTemporary: true,
                        model: this.threadModel,
                    }),
                });
                this.thread.cache.update({ messages: link(message) });
            }
        }

        /**
         * @private
         */
        _onThreadIsLoadingAttachmentsChanged() {
            if (!this.thread || !this.thread.isLoadingAttachments) {
                this._stopAttachmentsLoading();
                this.update({ isShowingAttachmentsLoading: false });
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
            this._attachmentsLoaderTimeout = this.messaging.browser.setTimeout(() => {
                this.update({ isShowingAttachmentsLoading: true });
                this._isPreparingAttachmentsLoading = false;
            }, this.messaging.loadingBaseDelayDuration);
        }

        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.messaging.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
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
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread'),
        /**
         * Determines the id of the thread that will be displayed by `this`.
         */
        threadId: attr(),
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
            compute: '_computeThreadViewer',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    };
    Chatter.onChanges = [
        new OnChange({
            dependencies: ['threadId', 'threadModel'],
            methodName: '_onThreadIdOrThreadModelChanged',
        }),
        new OnChange({
            dependencies: ['thread.isLoadingAttachments'],
            methodName: '_onThreadIsLoadingAttachmentsChanged',
        }),
    ];

    Chatter.modelName = 'mail.chatter';

    return Chatter;
}

registerNewModel('mail.chatter', factory);
