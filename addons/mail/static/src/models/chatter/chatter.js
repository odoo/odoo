/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, link, unlink } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

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
    identifyingFields: ['id'],
    lifecycleHooks: {
        _created() {
            this._attachmentsLoaderTimeout = undefined;
            this._isPreparingAttachmentsLoading = undefined;
        },
        _willDelete() {
            this._stopAttachmentsLoading();
        },
    },
    recordMethods: {
        focus() {
            if (this.composerView) {
                this.composerView.update({ doFocus: true });
            }
        },
        /**
         * Handles click on the attachments button.
         *
         * @param {MouseEvent} ev
         */
        onClickButtonAttachments(ev) {
            this.update({ attachmentBoxView: this.attachmentBoxView ? clear() : insertAndReplace() });
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
                    on_close: () => this.reloadParentView(),
                },
            });
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
            if (this.component) {
                const options = { keepChanges: true };
                if (fieldNames) {
                    options.fieldNames = fieldNames;
                }
                this.component.trigger('reload', options);
            }
        },
        showLogNote() {
            this.update({ composerView: insertAndReplace() });
            this.composerView.composer.update({ isLog: true });
            this.focus();
        },
        showSendMessage() {
            this.update({ composerView: insertAndReplace() });
            this.composerView.composer.update({ isLog: false });
            this.focus();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActivityBoxView() {
            if (this.thread && this.thread.hasActivities && this.thread.activities.length > 0) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return Boolean(this.thread && this.hasMessageList);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDisabled() {
            return Boolean(!this.thread || this.thread.isTemporary || !this.thread.hasReadAccess);
        },
        /**
         * @private
         * @returns {ThreadViewer}
         */
        _computeThreadViewer() {
            return insertAndReplace({
                hasThreadView: this.hasThreadView,
                order: 'desc',
                thread: this.thread ? link(this.thread) : unlink(),
            });
        },
        /**
         * @private
         */
        _onThreadIdOrThreadModelChanged() {
            if (this.threadId) {
                if (this.thread && this.thread.isTemporary) {
                    this.thread.delete();
                }
                this.update({
                    attachmentBoxView: this.isAttachmentBoxVisibleInitially ? insertAndReplace() : clear(),
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
                const message = this.messaging.models['Message'].create({
                    author: link(currentPartner),
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
                this.thread.cache.update({ messages: link(message) });
            }
        },
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
        },
        /**
         * @private
         */
        _prepareAttachmentsLoading() {
            this._isPreparingAttachmentsLoading = true;
            this._attachmentsLoaderTimeout = this.messaging.browser.setTimeout(() => {
                this.update({ isShowingAttachmentsLoading: true });
                this._isPreparingAttachmentsLoading = false;
            }, this.messaging.loadingBaseDelayDuration);
        },
        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.messaging.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
            this._isPreparingAttachmentsLoading = false;
        },
    },
    fields: {
        activityBoxView: one('ActivityBoxView', {
            compute: '_computeActivityBoxView',
            inverse: 'chatter',
            isCausal: true,
        }),
        attachmentBoxView: one('AttachmentBoxView', {
            inverse: 'chatter',
            isCausal: true,
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
        hasParentReloadOnAttachmentsChanged: attr({
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
            compute: '_computeThreadViewer',
            inverse: 'chatter',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['threadId', 'threadModel'],
            methodName: '_onThreadIdOrThreadModelChanged',
        }),
        new OnChange({
            dependencies: ['thread.isLoadingAttachments'],
            methodName: '_onThreadIsLoadingAttachmentsChanged',
        }),
    ],
});
