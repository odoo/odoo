odoo.define('mail/static/src/models/chatter/chatter.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');

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
        delete() {
            this._stopAttachmentsLoading();
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        async refresh() {
            const thread = this.thread;
            if (!thread || thread.isTemporary) {
                return;
            }
            thread.loadNewMessages();
            if (!this._isPreparingAttachmentsLoading && !this.isShowingAttachmentsLoading) {
                this._prepareAttachmentsLoading();
            }
            await thread.fetchAttachments();
            this._stopAttachmentsLoading();
        }

        async refreshActivities() {
            // A bit "extreme", may be improved
            const [{ activity_ids: newActivityIds }] = await this.async(() => this.env.services.rpc({
                model: this.thread.model,
                method: 'read',
                args: [this.thread.id, ['activity_ids']]
            }));
            const activitiesData = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [newActivityIds]
            }));
            const activities = [];
            for (const activityData of activitiesData) {
                const activity = this.env.models['mail.activity'].insert(
                    this.env.models['mail.activity'].convertData(activityData)
                );
                activities.push(activity);
            }
            this.update({ activities: [['replace', activities]] });
        }

        showLogNote() {
            this.update({ isComposerVisible: true });
            this.thread.composer.update({
                isDoFocus: true,
                isLog: true,
            });
        }

        showSendMessage() {
            this.update({ isComposerVisible: true });
            this.thread.composer.update({
                isDoFocus: true,
                isLog: false,
            });
        }

        toggleActivityBoxVisibility() {
            this.update({ isActivityBoxVisible: !this.isActivityBoxVisible });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeFutureActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'planned')]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDisabled() {
            return !this.threadId;
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeOverdueActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'overdue')]];
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeTodayActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'today')]];
        }

        /**
         * @private
         */
        _prepareAttachmentsLoading() {
            this._isPreparingAttachmentsLoading = true;
            this._attachmentsLoaderTimeout = this.env.browser.setTimeout(() => {
                this.update({isShowingAttachmentsLoading: true});
                this._isPreparingAttachmentsLoading = false;
            }, this.env.loadingBaseDelayDuration);
        }

        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.env.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
            this.update({isShowingAttachmentsLoading: false});
            this._isPreparingAttachmentsLoading = false;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            // thread
            if (
                this.threadModel !== previous.threadModel ||
                this.threadId !== previous.threadId
            ) {
                // change of thread
                this._updateRelationThread();
                if (previous.thread && previous.thread.isTemporary) {
                    // AKU FIXME: make dedicated models for "temporary" threads,
                    // so that it auto-handles causality of messages for deletion
                    // automatically
                    const oldMainThreadCache = previous.thread.mainCache;
                    const message = oldMainThreadCache.messages[0];
                    message.delete();
                    previous.thread.delete();
                }
            }

            if (previous.activityIds.join(',') !== this.activityIds.join(',')) {
                this.refreshActivities();
            }
            if (
                previous.followerIds.join(',') !== this.followerIds.join(',') &&
                !this.thread.isTemporary
            ) {
                this.thread.refreshFollowers();
            }
            if (
                previous.thread !== this.thread ||
                (this.thread && this.messageIds.join(',') !== previous.messageIds.join(','))
            ) {
                this.refresh();
            }
        }

        /**
         * @override
         */
        _updateBefore() {
            return {
                activityIds: this.activityIds,
                followerIds: this.followerIds,
                messageIds: this.messageIds,
                threadModel: this.threadModel,
                threadId: this.threadId,
                thread: this.thread,
            };
        }

        /**
         * @private
         */
        _updateRelationThread() {
            if (!this.threadId) {
                if (this.thread && this.thread.isTemporary) {
                    return;
                }
                const nextId = getThreadNextTemporaryId();
                const thread = this.env.models['mail.thread'].create({
                    areAttachmentsLoaded: true,
                    id: nextId,
                    isTemporary: true,
                    model: this.threadModel,
                });
                const currentPartner = this.env.messaging.currentPartner;
                const message = this.env.models['mail.message'].create({
                    author: [['link', currentPartner]],
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                this.threadViewer.update({ thread: [['link', thread]] });
                for (const cache of thread.caches) {
                    cache.update({ messages: [['link', message]] });
                }
            } else {
                // thread id and model
                const thread = this.env.models['mail.thread'].insert({
                    id: this.threadId,
                    model: this.threadModel,
                });
                this.threadViewer.update({ thread: [['link', thread]] });
            }
        }

    }

    Chatter.fields = {
        activities: one2many('mail.activity', {
            inverse: 'chatter',
        }),
        activityIds: attr({
            default: [],
        }),
        activitiesState: attr({
            related: 'activities.state',
        }),
        composer: many2one('mail.composer', {
            related: 'thread.composer',
        }),
        context: attr({
            default: {},
        }),
        followerIds: attr({
            default: [],
        }),
        futureActivities: one2many('mail.activity', {
            compute: '_computeFutureActivities',
            dependencies: ['activitiesState'],
        }),
        hasActivities: attr({
            default: true,
        }),
        hasExternalBorder: attr({
            default: true,
        }),
        hasFollowers: attr({
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
        hasThread: attr({
            default: true,
        }),
        hasTopbarCloseButton: attr({
            default: false,
        }),
        isActivityBoxVisible: attr({
            default: true,
        }),
        isAttachmentBoxVisible: attr({
            default: false,
        }),
        isComposerVisible: attr({
            default: false,
        }),
        isDisabled: attr({
            compute: '_computeIsDisabled',
            default: false,
            dependencies: ['threadId'],
        }),
        isShowingAttachmentsLoading: attr({
            default: false,
        }),
        messageIds: attr({
            default: [],
        }),
        overdueActivities: one2many('mail.activity', {
            compute: '_computeOverdueActivities',
            dependencies: ['activitiesState'],
        }),
        thread: many2one('mail.thread', {
            related: 'threadViewer.thread',
        }),
        threadAttachmentCount: attr({
            default: 0,
        }),
        threadId: attr(),
        threadModel: attr(),
        threadViewer: one2one('mail.thread_viewer', {
            autocreate: true,
        }),
        todayActivities: one2many('mail.activity', {
            compute: '_computeTodayActivities',
            dependencies: ['activitiesState'],
        }),
    };

    Chatter.modelName = 'mail.chatter';

    return Chatter;
}

registerNewModel('mail.chatter', factory);

});
