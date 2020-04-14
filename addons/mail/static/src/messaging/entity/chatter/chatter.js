odoo.define('mail.messaging.entity.Chatter', function (require) {
'use strict';

const {
    fields: {
        one2many,
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function ChatterFactory({ Entity }) {

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

    class Chatter extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {mail.messaging.entity.Activity[]}
         */
        get futureActivities() {
            return this.activities.filter(activity => activity.state === 'planned');
        }

        /**
         * @returns {mail.messaging.entity.Activity[]}
         */
        get overdueActivities() {
            return this.activities.filter(activity => activity.state === 'overdue');
        }

        refresh() {
            const thread = this.thread;
            if (!thread || thread.isTemporary) {
                return;
            }
            thread.loadNewMessages();
            thread.fetchAttachments();
        }

        async refreshActivities() {
            // A bit "extreme", may be improved
            const [{ activity_ids: newActivityIds }] = await this.env.rpc({
                model: this.thread.model,
                method: 'read',
                args: [this.thread.id, ['activity_ids']]
            });
            const activitiesData = await this.env.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [newActivityIds]
            });
            const activities = [];
            for (const activityData of activitiesData) {
                const activity = this.env.entities.Activity.insert(activityData);
                activities.push(activity);
            }
            const oldPrevActivities = this.activities.filter(
                activity => !activities.includes(activity)
            );
            const newActivities = activities.filter(
                activity => !this.activities.includes(activity)
            );
            this.unlink({ activities: oldPrevActivities });
            this.link({ activities: newActivities });
        }

        showLogNote() {
            this.update({
                isComposerLog: true,
                isComposerVisible: true,
            });
        }

        showSendMessage() {
            this.update({
                isComposerLog: false,
                isComposerVisible: true,
            });
        }

        /**
         * @returns {mail.messaging.entity.Thread}
         */
        get thread() {
            return this.threadViewer && this.threadViewer.thread;
        }

        /**
         * @returns {mail.messaging.entity.Activity[]}
         */
        get todayActivities() {
            return this.activities.filter(activity => activity.state === 'today');
        }

        toggleActivityBoxVisibility() {
            this.update({ isActivityBoxVisible: !this.isActivityBoxVisible });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         * @param {integer} [data.threadId]
         * @param {string} [data.threadModel]
         */
        _update(data) {
            const prevActivityIds = this.activityIds || [];
            const prevMessageIds = this.messageIds || [];
            const prevThreadModel = this.threadModel;
            const prevThreadId = this.threadId;
            const prevThread = this.thread;

            const {
                activityIds = this.activityIds || [],
                context = this.context || {},
                followerIds = this.followerIds || [],
                hasActivities = this.hasActivities || true,
                hasFollowers = this.hasFollowers || true,
                hasThread = this.hasThread || true,
                isActivityBoxVisible = this.isActivityBoxVisible || false,
                isAttachmentBoxVisible = this.isAttachmentBoxVisible || false,
                isComposerLog = this.isComposerLog || true,
                isComposerVisible = this.isComposerVisible || false,
                messageIds = this.messageIds || [],
                threadId = this.threadId,
                threadModel = this.threadModel,
            } = data;

            if (!this.threadViewer) {
                const threadViewer = this.env.entities.ThreadViewer.create();
                this.link({ threadViewer });
            }

            Object.assign(this, {
                activityIds,
                context,
                followerIds,
                hasActivities,
                hasFollowers,
                hasThread,
                isActivityBoxVisible,
                isAttachmentBoxVisible,
                isComposerLog,
                isComposerVisible,
                isDisabled: threadId ? false : true,
                messageIds,
                threadId,
                threadModel,
            });

            // thread
            if (
                this.threadModel !== prevThreadModel ||
                this.threadId !== prevThreadId ||
                (this.threadId === prevThreadId && prevThreadId === undefined)
            ) {
                // change of thread
                this._updateRelationThread();
                if (prevThread && prevThread.isTemporary) {
                    // AKU FIXME: make dedicated models for "temporary" threads,
                    // so that it auto-handles causality of messages for deletion
                    // automatically
                    const oldMainThreadCache = prevThread.mainCache;
                    const message = oldMainThreadCache.messages[0];
                    message.delete();
                    prevThread.delete();
                }
            }

            if (prevActivityIds.join(',') !== this.activityIds.join(',')) {
                this.refreshActivities();
            }
            if (
                this.threadId !== prevThreadId ||
                this.threadModel !== prevThreadModel ||
                this.messageIds.join(',') !== prevMessageIds.join(',')
            ) {
                this.refresh();
            }
        }

        /**
         * @private
         */
        _updateRelationThread() {
            if (!this.threadId) {
                const nextId = getThreadNextTemporaryId();
                const thread = this.env.entities.Thread.create({
                    areAttachmentsLoaded: true,
                    id: nextId,
                    isTemporary: true,
                    model: this.threadModel,
                });
                const currentPartner = this.env.messaging.currentPartner;
                const message = this.env.entities.Message.create({
                    author_id: [currentPartner.id, currentPartner.display_name],
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                this.threadViewer.update({ thread });
                for (const cache of thread.caches) {
                    cache.link({ messages: message });
                }
            } else {
                // thread id and model
                let thread = this.env.entities.Thread.fromModelAndId({
                    id: this.threadId,
                    model: this.threadModel,
                });
                if (!thread) {
                    thread = this.env.entities.Thread.create({
                        id: this.threadId,
                        model: this.threadModel,
                    });
                }
                this.threadViewer.update({ thread });
            }
        }

    }

    Object.assign(Chatter, {
        fields: Object.assign({}, Entity.fields, {
            activities: one2many('Activity', {
                inverse: 'chatter',
            }),
            threadViewer: one2one('ThreadViewer', {
                inverse: 'chatter',
            }),
        }),
    });

    return Chatter;
}

registerNewEntity('Chatter', ChatterFactory);

});
