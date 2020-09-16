odoo.define('mail/static/src/models/chatter/chatter.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

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
            this.update({
                __mfield_isDoFocus: true,
            });
        }

        async refresh() {
            const thread = this.__mfield_thread(this);
            if (!thread || thread.__mfield_isTemporary(this)) {
                return;
            }
            thread.loadNewMessages();
            if (
                !this._isPreparingAttachmentsLoading &&
                !this.__mfield_isShowingAttachmentsLoading(this)
            ) {
                this._prepareAttachmentsLoading();
            }
            await thread.fetchAttachments();
            this._stopAttachmentsLoading();
        }

        async refreshActivities() {
            if (!this.__mfield_hasActivities(this)) {
                return;
            }
            if (
                !this.__mfield_thread(this) ||
                this.__mfield_thread(this).__mfield_isTemporary(this)
            ) {
                this.update({
                    __mfield_activities: [['unlink-all']],
                });
                return;
            }
            // A bit "extreme", may be improved
            const [{ activity_ids: newActivityIds }] = await this.async(() => this.env.services.rpc({
                model: this.__mfield_thread(this).__mfield_model(this),
                method: 'read',
                args: [this.__mfield_thread(this).__mfield_id(this), ['activity_ids']]
            }));
            const activitiesData = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [newActivityIds]
            }));
            const activities = this.env.models['mail.activity'].insert(activitiesData.map(
                activityData => this.env.models['mail.activity'].convertData(activityData)
            ));
            this.update({
                __mfield_activities: [['replace', activities]],
            });
        }

        showLogNote() {
            this.update({
                __mfield_isComposerVisible: true,
            });
            this.__mfield_thread(this).__mfield_composer(this).update({
                __mfield_isLog: true,
            });
            this.focus();
        }

        showSendMessage() {
            this.update({
                __mfield_isComposerVisible: true,
            });
            this.__mfield_thread(this).__mfield_composer(this).update({
                __mfield_isLog: false,
            });
            this.focus();
        }

        toggleActivityBoxVisibility() {
            this.update({
                __mfield_isActivityBoxVisible: !this.__mfield_isActivityBoxVisible(this),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeFutureActivities() {
            return [['replace',
                this.__mfield_activities(this).filter(activity =>
                    activity.__mfield_state(this) === 'planned'
                )
            ]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return this.__mfield_thread(this) && this.__mfield_hasMessageList(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDisabled() {
            return !this.__mfield_threadId(this);
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeOverdueActivities() {
            return [['replace',
                this.__mfield_activities(this).filter(activity =>
                    activity.__mfield_state(this) === 'overdue'
                )
            ]];
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeTodayActivities() {
            return [['replace',
                this.__mfield_activities(this).filter(activity =>
                    activity.__mfield_state(this) === 'today'
                )
            ]];
        }

        /**
         * @private
         */
        _prepareAttachmentsLoading() {
            this._isPreparingAttachmentsLoading = true;
            this._attachmentsLoaderTimeout = this.env.browser.setTimeout(() => {
                this.update({
                    __mfield_isShowingAttachmentsLoading: true,
                });
                this._isPreparingAttachmentsLoading = false;
            }, this.env.loadingBaseDelayDuration);
        }

        /**
         * @private
         */
        _stopAttachmentsLoading() {
            this.env.browser.clearTimeout(this._attachmentsLoaderTimeout);
            this._attachmentsLoaderTimeout = null;
            this.update({
                __mfield_isShowingAttachmentsLoading: false,
            });
            this._isPreparingAttachmentsLoading = false;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            // thread
            if (
                this.__mfield_threadModel(this) !== previous.threadModel ||
                this.__mfield_threadId(this) !== previous.threadId
            ) {
                // change of thread
                this._updateRelationThread();
                if (
                    previous.thread &&
                    previous.thread.__mfield_isTemporary(this)
                ) {
                    // AKU FIXME: make dedicated models for "temporary" threads,
                    // so that it auto-handles causality of messages for deletion
                    // automatically
                    const oldMainThreadCache = previous.thread.__mfield_mainCache(this);
                    const message = oldMainThreadCache.__mfield_messages(this)[0];
                    message.delete();
                    previous.thread.delete();
                }
            }

            if (
                !previous.activityIds ||
                previous.activityIds.join(',') !== this.__mfield_activityIds(this).join(',')
            ) {
                this.refreshActivities();
            }
            if (
                !previous.followerIds ||
                previous.followerIds.join(',') !== this.__mfield_followerIds(this).join(',')
            ) {
                if (this.__mfield_thread(this)) {
                    this.__mfield_thread(this).refreshFollowers();
                    this.__mfield_thread(this).fetchAndUpdateSuggestedRecipients();
                }
            }
            if (
                !previous.messageIds ||
                previous.thread !== this.__mfield_thread(this) ||
                this.__mfield_messageIds(this).join(',') !== previous.messageIds.join(',')
            ) {
                this.refresh();
            }
        }

        /**
         * @override
         */
        _updateBefore() {
            return {
                activityIds: this.__mfield_activityIds(this),
                followerIds: this.__mfield_followerIds(this),
                messageIds: this.__mfield_messageIds(this),
                threadModel: this.__mfield_threadModel(this),
                threadId: this.__mfield_threadId(this),
                thread: this.__mfield_thread(this),
            };
        }

        /**
         * @private
         */
        _updateRelationThread() {
            if (!this.__mfield_threadId(this)) {
                if (
                    this.__mfield_thread(this) &&
                    this.__mfield_thread(this).__mfield_isTemporary(this)
                ) {
                    return;
                }
                const nextId = getThreadNextTemporaryId();
                const thread = this.env.models['mail.thread'].create({
                    __mfield_areAttachmentsLoaded: true,
                    __mfield_id: nextId,
                    __mfield_isTemporary: true,
                    __mfield_model: this.__mfield_threadModel(this),
                });
                const currentPartner = this.env.messaging.__mfield_currentPartner(this);
                const message = this.env.models['mail.message'].create({
                    __mfield_author: [['link', currentPartner]],
                    __mfield_body: this.env._t("Creating a new record..."),
                    __mfield_id: getMessageNextTemporaryId(),
                    __mfield_isTemporary: true,
                });
                this.update({
                    __mfield_thread: [['link', thread]],
                });
                for (const cache of thread.__mfield_caches(this)) {
                    cache.update({
                        __mfield_messages: [['link', message]],
                    });
                }
            } else {
                // thread id and model
                const thread = this.env.models['mail.thread'].insert({
                    __mfield_id: this.__mfield_threadId(this),
                    __mfield_model: this.__mfield_threadModel(this),
                });
                this.update({
                    __mfield_thread: [['link', thread]],
                });
            }
        }

    }

    Chatter.fields = {
        __mfield_activities: one2many('mail.activity', {
            inverse: '__mfield_chatter',
        }),
        __mfield_activityIds: attr({
            default: [],
        }),
        __mfield_activitiesState: attr({
            related: '__mfield_activities.__mfield_state',
        }),
        __mfield_composer: many2one('mail.composer', {
            related: '__mfield_thread.__mfield_composer',
        }),
        __mfield_context: attr({
            default: {},
        }),
        __mfield_followerIds: attr({
            default: [],
        }),
        __mfield_futureActivities: one2many('mail.activity', {
            compute: '_computeFutureActivities',
            dependencies: [
                '__mfield_activitiesState',
            ],
        }),
        __mfield_hasActivities: attr({
            default: true,
        }),
        __mfield_hasExternalBorder: attr({
            default: true,
        }),
        __mfield_hasFollowers: attr({
            default: true,
        }),
        /**
         * Determines whether `this` should display a message list.
         */
        __mfield_hasMessageList: attr({
            default: true,
        }),
        /**
         * Whether the message list should manage its scroll.
         * In particular, when the chatter is on the form view's side,
         * then the scroll is managed by the message list.
         * Also, the message list shoud not manage the scroll if it shares it
         * with the rest of the page.
         */
        __mfield_hasMessageListScrollAdjust: attr({
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        __mfield_hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                '__mfield_hasMessageList',
                '__mfield_thread',
            ],
        }),
        __mfield_hasTopbarCloseButton: attr({
            default: false,
        }),
        __mfield_isActivityBoxVisible: attr({
            default: true,
        }),
        __mfield_isAttachmentBoxVisible: attr({
            default: false,
        }),
        __mfield_isComposerVisible: attr({
            default: false,
        }),
        __mfield_isDisabled: attr({
            compute: '_computeIsDisabled',
            default: false,
            dependencies: [
                '__mfield_threadId',
            ],
        }),
        /**
         * Determine whether this chatter should be focused at next render.
         */
        __mfield_isDoFocus: attr({
            default: false,
        }),
        __mfield_isShowingAttachmentsLoading: attr({
            default: false,
        }),
        __mfield_messageIds: attr({
            default: [],
        }),
        __mfield_overdueActivities: one2many('mail.activity', {
            compute: '_computeOverdueActivities',
            dependencies: [
                '__mfield_activitiesState',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        __mfield_thread: many2one('mail.thread'),
        __mfield_threadAttachmentCount: attr({
            default: 0,
        }),
        __mfield_threadId: attr(),
        __mfield_threadModel: attr(),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        __mfield_threadView: one2one('mail.thread_view', {
            related: '__mfield_threadViewer.__mfield_threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        __mfield_threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: '__mfield_chatter',
            isCausal: true,
        }),
        __mfield_todayActivities: one2many('mail.activity', {
            compute: '_computeTodayActivities',
            dependencies: [
                '__mfield_activitiesState'
            ],
        }),
    };

    Chatter.modelName = 'mail.chatter';

    return Chatter;
}

registerNewModel('mail.chatter', factory);

});
