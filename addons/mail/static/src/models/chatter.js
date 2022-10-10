/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insert, link } from '@mail/model/model_field_command';

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

registerModel({
    name: 'Chatter',
    recordMethods: {
        focus() {
            if (this.composerView) {
                this.composerView.update({ doFocus: true });
            }
        },
        onAttachmentsLoadingTimeout() {
            this.update({
                attachmentsLoaderTimer: clear(),
                isShowingAttachmentsLoading: true,
            });
        },
        /**
         * Handles click on the attach button.
         */
        onClickButtonAddAttachments() {
            this.fileUploader.openBrowserFileUploader();
        },
        /**
         * Handles click on the attachments button.
         */
        onClickButtonToggleAttachments() {
            this.update({ attachmentBoxView: this.attachmentBoxView ? clear() : {} });
        },
        /**
         * Handles click on top bar close button.
         *
         * @param {MouseEvent} ev
         */
        onClickChatterTopbarClose(ev) {
            this.component.trigger('o-close-chatter');
        },
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
        },
        /**
         * Handles click on "schedule activity" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickScheduleActivity(ev) {
            await this.messaging.openActivityForm({ thread: this.thread });
            if (this.exists()) {
                this.reloadParentView();
            }
        },
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
        },
        /**
         * Handles scroll on this scroll panel.
         *
         * @param {Event} ev
         */
        onScrollScrollPanel(ev) {
            if (!this.threadView || !this.threadView.messageListView || !this.threadView.messageListView.component) {
                return;
            }
            this.threadView.messageListView.component.onScroll(ev);
        },
        openAttachmentBoxView() {
            this.update({ attachmentBoxView: {} });
        },
        /**
         * Open a dialog to add partners as followers.
         */
        promptAddPartnerFollower() {
            const action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.wizard.invite',
                view_mode: 'form',
                views: [[false, 'form']],
                name: this.env._t("Invite Follower"),
                target: 'new',
                context: {
                    default_res_model: this.thread.model,
                    default_res_id: this.thread.id,
                },
            };
            this.env.services.action.doAction(
                action,
                {
                    onClose: async () => {
                        if (!this.exists() && !this.thread) {
                            return;
                        }
                        await this.thread.fetchData(['followers']);
                        if (this.exists() && this.hasParentReloadOnFollowersUpdate) {
                            this.reloadParentView();
                        }
                    },
                }
            );
        },
        async refresh() {
            const requestData = ['activities', 'followers', 'suggestedRecipients'];
            if (this.hasMessageList) {
                requestData.push('attachments', 'messages');
            }
            this.thread.fetchData(requestData);
        },
        /**
         * @param {Object} [param0={}]
         * @param {string[]} [fieldNames]
         */
        reloadParentView({ fieldNames } = {}) {
            if (this.webRecord) {
                this.webRecord.model.load({ resId: this.threadId });
                return;
            }
            if (this.component) {
                const options = { keepChanges: true };
                if (fieldNames) {
                    options.fieldNames = fieldNames;
                }
                this.component.trigger('reload', options);
            }
        },
        showLogNote() {
            this.update({ composerView: {} });
            this.composerView.composer.update({ isLog: true });
            this.focus();
        },
        showSendMessage() {
            this.update({ composerView: {} });
            this.composerView.composer.update({ isLog: false });
            this.focus();
        },
        /**
         * @private
         */
        _onThreadIdOrThreadModelChanged() {
            if (!this.threadModel) {
                return;
            }
            if (this.threadId) {
                if (this.thread && this.thread.isTemporary) {
                    this.thread.delete();
                }
                this.update({
                    attachmentBoxView: this.isAttachmentBoxVisibleInitially ? {} : clear(),
                    thread: insert({
                        // If the thread was considered to have the activity
                        // mixin once, it will have it forever.
                        hasActivities: this.hasActivities ? true : undefined,
                        id: this.threadId,
                        model: this.threadModel,
                    }),
                });
            } else if (!this.thread || !this.thread.isTemporary) {
                const currentPartner = this.messaging.currentPartner;
                const message = this.messaging.models['Message'].insert({
                    author: currentPartner,
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                const nextId = getThreadNextTemporaryId();
                this.update({
                    attachmentBoxView: clear(),
                    thread: insert({
                        areAttachmentsLoaded: true,
                        id: nextId,
                        isTemporary: true,
                        model: this.threadModel,
                    }),
                });
                this.thread.cache.update({ temporaryMessages: link(message) });
            }
        },
        /**
         * @private
         */
        _onThreadIsLoadingAttachmentsChanged() {
            if (!this.thread || !this.thread.isLoadingAttachments) {
                this.update({
                    attachmentsLoaderTimer: clear(),
                    isShowingAttachmentsLoading: false,
                });
                return;
            }
            if (this.isPreparingAttachmentsLoading || this.isShowingAttachmentsLoading) {
                return;
            }
            this._prepareAttachmentsLoading();
        },
        /**
         * @private
         */
        _prepareAttachmentsLoading() {
            this.update({ attachmentsLoaderTimer: {} });
        },
    },
    fields: {
        activityBoxView: one('ActivityBoxView', {
            compute() {
                if (this.thread && this.thread.hasActivities && this.thread.activities.length > 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatter',
        }),
        attachmentBoxView: one('AttachmentBoxView', {
            inverse: 'chatter',
        }),
        attachmentsLoaderTimer: one('Timer', {
            inverse: 'chatterOwnerAsAttachmentsLoader',
        }),
        /**
         * States the OWL Chatter component of this chatter.
         */
        component: attr(),
        /**
         * Determines the composer view used to post in this chatter (if any).
         */
        composerView: one('ComposerView', {
            inverse: 'chatter',
        }),
        context: attr({
            default: {},
        }),
        dropZoneView: one('DropZoneView', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (this.useDragVisibleDropZone.isVisible) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatterOwner',
        }),
        fileUploader: one('FileUploader', {
            compute() {
                return this.thread ? {} : clear();
            },
            inverse: 'chatterOwner',
        }),
        followButtonView: one('FollowButtonView', {
            compute() {
                if (this.hasFollowers && this.thread && (!this.thread.channel || this.thread.channel.channel_type !== 'chat')) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatterOwner',
        }),
        followerListMenuView: one('FollowerListMenuView', {
            compute() {
                if (this.hasFollowers && this.thread) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatterOwner',
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
        hasParentReloadOnAttachmentsChanged: attr({
            default: false,
        }),
        hasParentReloadOnFollowersUpdate: attr({
            default: false,
        }),
        hasParentReloadOnMessagePosted: attr({
            default: false,
        }),
        hasReadAccess: attr({
            compute() {
                return Boolean(this.thread && !this.thread.isTemporary && this.thread.hasReadAccess);
            },
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute() {
                return Boolean(this.thread && this.hasMessageList);
            },
        }),
        hasWriteAccess: attr({
            compute() {
                return Boolean(this.thread && !this.thread.isTemporary && this.thread.hasWriteAccess);
            },
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
            identifying: true,
        }),
        /**
         * Determiners whether the attachment box is visible initially.
         */
        isAttachmentBoxVisibleInitially: attr({
            default: false,
        }),
        isInFormSheetBg: attr({
            default: false,
        }),
        isPreparingAttachmentsLoading: attr({
            compute() {
                return Boolean(this.attachmentsLoaderTimer);
            },
            default: false,
        }),
        isShowingAttachmentsLoading: attr({
            default: false,
        }),
        scrollPanelRef: attr(),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         */
        thread: one('Thread'),
        /**
         * Determines the id of the thread that will be displayed by `this`.
         */
        threadId: attr(),
        /**
         * Determines the model of the thread that will be displayed by `this`.
         */
        threadModel: attr(),
        /**
         * States the `ThreadView` displaying `this.thread`.
         */
        threadView: one('ThreadView', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `ThreadViewer` managing the display of `this.thread`.
         */
        threadViewer: one('ThreadViewer', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return {
                    hasThreadView: this.hasThreadView,
                    order: 'desc',
                    thread: this.thread ? this.thread : clear(),
                };
            },
            inverse: 'chatter',
        }),
        topbar: one('ChatterTopbar', {
            compute() {
                return this.thread ? {} : clear();
            },
            inverse: 'chatter',
        }),
        useDragVisibleDropZone: one('UseDragVisibleDropZone', {
            default: {},
            inverse: 'chatterOwner',
            readonly: true,
            required: true,
        }),
        webRecord: attr(),
    },
    onChanges: [
        {
            dependencies: ['threadId', 'threadModel'],
            methodName: '_onThreadIdOrThreadModelChanged',
        },
        {
            dependencies: ['thread.isLoadingAttachments'],
            methodName: '_onThreadIsLoadingAttachmentsChanged',
        },
    ],
});
