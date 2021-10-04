/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, link, unlink } from '@mail/model/model_field_command';
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
            this._attachmentsLoaderTimeout = undefined;
            this._isPreparingAttachmentsLoading = undefined;
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickActivityBoxTitle = this.onClickActivityBoxTitle.bind(this);
            this.onClickButtonAttachments = this.onClickButtonAttachments.bind(this);
            this.onClickChatterTopbarClose = this.onClickChatterTopbarClose.bind(this);
            this.onClickLogNote = this.onClickLogNote.bind(this);
            this.onClickScheduleActivity = this.onClickScheduleActivity.bind(this);
            this.onClickSendMessage = this.onClickSendMessage.bind(this);
            this.onScrollScrollPanel = this.onScrollScrollPanel.bind(this);
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
            if (this.composerView) {
                this.composerView.update({ doFocus: true });
            }
        }

        /**
         * Handles click on activity box title.
         *
         * @param {MouseEvent} ev
         */
        onClickActivityBoxTitle(ev) {
            this.update({ isActivityBoxVisible: !this.isActivityBoxVisible });
        }

        /**
         * Handles click on the attachments button.
         *
         * @param {MouseEvent} ev
         */
        onClickButtonAttachments(ev) {
            this.update({ isAttachmentBoxVisible: !this.isAttachmentBoxVisible });
        }

        /**
         * Handles click on top bar close button.
         *
         * @param {MouseEvent} ev
         */
        onClickChatterTopbarClose(ev) {
            this.componentChatterTopbar.trigger('o-close-chatter');
        }

        /**
         * Handles click on "log note" button.
         *
         * @param {MouseEvent} ev
         */
        onClickLogNote() {
            if (this.composerView && this.composerView.composer.isLog) {
                this.update({ composerView: clear() });
            } else {
                this.showLogNote();
            }
        }

        /**
         * Handles click on "schedule activity" button.
         *
         * @param {MouseEvent} ev
         */
        onClickScheduleActivity(ev) {
            const action = {
                type: 'ir.actions.act_window',
                name: this.env._t("Schedule Activity"),
                res_model: 'mail.activity',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: this.thread.id,
                    default_res_model: this.thread.model,
                },
                res_id: false,
            };
            return this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        if (!this.componentChatterTopbar) {
                            return;
                        }
                        this.componentChatterTopbar.trigger('reload', { keepChanges: true });
                    },
                },
            });
        }

        /**
         * Handles click on "send message" button.
         *
         * @param {MouseEvent} ev
         */
        onClickSendMessage(ev) {
            if (this.composerView && !this.composerView.composer.isLog) {
                this.update({ composerView: clear() });
            } else {
                this.showSendMessage();
            }
        }

        /**
         * Handles scroll on this scroll panel.
         *
         * @param {Event} ev
         */
        onScrollScrollPanel(ev) {
            if (!this.threadRef.comp) {
                return;
            }
            this.threadRef.comp.onScroll(ev);
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
            this.update({ composerView: insertAndReplace() });
            this.composerView.composer.update({ isLog: true });
            this.focus();
        }

        showSendMessage() {
            this.update({ composerView: insertAndReplace() });
            this.composerView.composer.update({ isLog: false });
            this.focus();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {boolean}
         */
        _computeAttachmentList() {
            return (this.thread && this.thread.allAttachments.length > 0)
                ? insertAndReplace()
                : clear();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return Boolean(this.thread && this.hasMessageList);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDisabled() {
            return Boolean(!this.thread || this.thread.isTemporary);
        }

        /**
         * @private
         * @returns {mail.thread_viewer}
         */
        _computeThreadViewer() {
            return insertAndReplace({
                hasThreadView: this.hasThreadView,
                order: 'desc',
                thread: this.thread ? link(this.thread) : unlink(),
            });
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
            this._attachmentsLoaderTimeout = this.env.browser.setTimeout(() => {
                this.update({ isShowingAttachmentsLoading: true });
                this._isPreparingAttachmentsLoading = false;
            }, this.messaging.loadingBaseDelayDuration);
        }

        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.env.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
            this._isPreparingAttachmentsLoading = false;
        }

    }

    Chatter.fields = {
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one2one('mail.attachment_list', {
            compute: '_computeAttachmentList',
            inverse: 'chatter',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the OWL component of this chatter top bar.
         */
        componentChatterTopbar: attr(),
        /**
         * Determines the composer view used to post in this chatter (if any).
         */
        composerView: one2one('mail.composer_view', {
            inverse: 'chatter',
            isCausal: true,
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
        /**
         * States the id of this chatter. This id does not correspond to any
         * specific value, it is just a unique identifier given by the creator
         * of this record.
         */
        id: attr({
            readonly: true,
            required: true,
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
        isDisabled: attr({
            compute: '_computeIsDisabled',
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
         * States the OWL ref of the "thread" (ThreadView) of this chatter.
         */
        threadRef: attr(),
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
            inverse: 'chatter',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    };
    Chatter.identifyingFields = ['id'];
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
