odoo.define('mail/static/src/models/message/message.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field_utils.js');
const { addLink, htmlToTextContentInline, parseAndTransform } = require('mail.utils');

const { str_to_datetime } = require('web.time');

function factory(dependencies) {

    class Message extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {mail.thread} thread
         * @param {string} threadStringifiedDomain
         */
        static checkAll(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            threadCache.update({
                __mfield_checkedMessages: [['link', threadCache.__mfield_messages()]],
            });
        }

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('attachment_ids' in data) {
                if (!data.attachment_ids) {
                    data2.__mfield_attachments = [['unlink-all']];
                } else {
                    data2.__mfield_attachments = [
                        ['insert-and-replace', data.attachment_ids.map(attachmentData =>
                            this.env.models['mail.attachment'].convertData(attachmentData)
                        )],
                    ];
                }
            }
            if ('author_id' in data) {
                if (!data.author_id) {
                    data2.__mfield_author = [['unlink-all']];
                } else if (data.author_id[0] !== 0) {
                    // partner id 0 is a hack of message_format to refer to an
                    // author non-related to a partner. display_name equals
                    // email_from, so this is omitted due to being redundant.
                    data2.__mfield_author = [
                        ['insert', {
                            __mfield_display_name: data.author_id[1],
                            __mfield_id: data.author_id[0],
                        }],
                    ];
                }
            }
            if ('body' in data) {
                data2.__mfield_body = data.body;
            }
            if ('channel_ids' in data && data.channel_ids) {
                const channels = data.channel_ids
                    .map(channelId =>
                        this.env.models['mail.thread'].findFromIdentifyingData({
                            __mfield_id: channelId,
                            __mfield_model: 'mail.channel',
                        })
                    ).filter(channel => !!channel);
                data2.__mfield_serverChannels = [['replace', channels]];
            }
            if ('date' in data && data.date) {
                data2.__mfield_date = moment(str_to_datetime(data.date));
            }
            if ('email_from' in data) {
                data2.__mfield_email_from = data.email_from;
            }
            if ('history_partner_ids' in data) {
                data2.__mfield_isHistory = data.history_partner_ids.includes(this.env.messaging.__mfield_currentPartner().__mfield_id());
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('is_discussion' in data) {
                data2.__mfield_is_discussion = data.is_discussion;
            }
            if ('is_note' in data) {
                data2.__mfield_is_note = data.is_note;
            }
            if ('is_notification' in data) {
                data2.__mfield_is_notification = data.is_notification;
            }
            if ('message_type' in data) {
                data2.__mfield_message_type = data.message_type;
            }
            if ('model' in data && 'res_id' in data && data.model && data.res_id) {
                const originThreadData = {
                    __mfield_id: data.res_id,
                    __mfield_model: data.model,
                };
                if ('record_name' in data && data.record_name) {
                    originThreadData.__mfield_name = data.record_name;
                }
                if ('res_model_name' in data && data.res_model_name) {
                    originThreadData.__mfield_model_name = data.res_model_name;
                }
                if ('module_icon' in data) {
                    originThreadData.__mfield_moduleIcon = data.module_icon;
                }
                data2.__mfield_originThread = [['insert', originThreadData]];
            }
            if ('moderation_status' in data) {
                data2.__mfield_moderation_status = data.moderation_status;
            }
            if ('needaction_partner_ids' in data) {
                data2.__mfield_isNeedaction = data.needaction_partner_ids.includes(this.env.messaging.__mfield_currentPartner().__mfield_id());
            }
            if ('notifications' in data) {
                data2.__mfield_notifications = [['insert', data.notifications.map(notificationData =>
                    this.env.models['mail.notification'].convertData(notificationData)
                )]];
            }
            if ('starred_partner_ids' in data) {
                data2.__mfield_isStarred = data.starred_partner_ids.includes(this.env.messaging.__mfield_currentPartner().__mfield_id());
            }
            if ('subject' in data) {
                data2.__mfield_subject = data.subject;
            }
            if ('subtype_description' in data) {
                data2.__mfield_subtype_description = data.subtype_description;
            }
            if ('subtype_id' in data) {
                data2.__mfield_subtype_id = data.subtype_id;
            }
            if ('tracking_value_ids' in data) {
                data2.__mfield_tracking_value_ids = data.tracking_value_ids;
            }

            return data2;
        }

        /**
         * Mark all messages of current user with given domain as read.
         *
         * @static
         * @param {Array[]} domain
         */
        static async markAllAsRead(domain) {
            await this.env.services.rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: { domain },
            });
        }

        /**
         * Mark provided messages as read. Messages that have been marked as
         * read are acknowledged by server with response as longpolling
         * notification of following format:
         *
         * [[dbname, 'res.partner', partnerId], { type: 'mark_as_read' }]
         *
         * @see mail.messaging_notification_handler:_handleNotificationPartnerMarkAsRead()
         *
         * @static
         * @param {mail.message[]} messages
         */
        static async markAsRead(messages) {
            await this.env.services.rpc({
                model: 'mail.message',
                method: 'set_message_done',
                args: [messages.map(message => message.__mfield_id(this))]
            });
        }

        /**
         * Applies the moderation `decision` on the provided messages.
         *
         * @static
         * @param {mail.message[]} messages
         * @param {string} decision: 'accept', 'allow', ban', 'discard', or 'reject'
         * @param {Object|undefined} [kwargs] optional data to pass on
         *  message moderation. This is provided when rejecting the messages
         *  for which title and comment give reason(s) for reject.
         * @param {string} [kwargs.title]
         * @param {string} [kwargs.comment]
         */
        static async moderate(messages, decision, kwargs) {
            const messageIds = messages.map(message => message.__mfield_id());
            await this.env.services.rpc({
                model: 'mail.message',
                method: 'moderate',
                args: [messageIds, decision],
                kwargs: kwargs,
            });
        }
        /**
         * Performs the `message_fetch` RPC on `mail.message`.
         *
         * @static
         * @param {Array[]} domain
         * @param {integer} [limit]
         * @param {integer[]} [moderated_channel_ids]
         * @param {Object} [context]
         * @returns {mail.message[]}
         */
        static async performRpcMessageFetch(domain, limit, moderated_channel_ids, context) {
            const messagesData = await this.env.services.rpc({
                model: 'mail.message',
                method: 'message_fetch',
                kwargs: {
                    context,
                    domain,
                    limit,
                    moderated_channel_ids,
                },
            }, { shadow: true });
            const messages = this.env.models['mail.message'].insert(messagesData.map(
                messageData => this.env.models['mail.message'].convertData(messageData)
            ));
            // compute seen indicators (if applicable)
            for (const message of messages) {
                for (const thread of message.__mfield_threads()) {
                    if (
                        thread.__mfield_model() !== 'mail.channel' ||
                        thread.__mfield_channel_type() === 'channel'
                    ) {
                        // disabled on non-channel threads and
                        // on `channel` channels for performance reasons
                        continue;
                    }
                    this.env.models['mail.message_seen_indicator'].insert({
                        __mfield_messageId: message.__mfield_id(this),
                        __mfield_threadId: thread.__mfield_id(this),
                    });
                }
            }
            return messages;
        }

        /**
         * @static
         * @param {mail.thread} thread
         * @param {string} threadStringifiedDomain
         */
        static uncheckAll(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            threadCache.update({
                __mfield_checkedMessages: [['unlink', threadCache.__mfield_messages()]],
            });
        }

        /**
         * Unstar all starred messages of current user.
         */
        static async unstarAll() {
            await this.env.services.rpc({
                model: 'mail.message',
                method: 'unstar_all',
            });
        }

        /**
         * @param {mail.thread} thread
         * @param {string} threadStringifiedDomain
         * @returns {boolean}
         */
        isChecked(thread, threadStringifiedDomain) {
            // aku todo
            const relatedCheckedThreadCache = this.__mfield_checkedThreadCaches(this).find(
                threadCache => (
                    threadCache.__mfield_thread(this) === thread &&
                    threadCache.__mfield_stringifiedDomain(this) === threadStringifiedDomain
                )
            );
            return !!relatedCheckedThreadCache;
        }

        /**
         * Mark this message as read, so that it no longer appears in current
         * partner Inbox.
         */
        async markAsRead() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'set_message_done',
                args: [[this.__mfield_id(this)]]
            }));
        }

        /**
         * Applies the moderation `decision` on this message.
         *
         * @param {string} decision: 'accept', 'allow', ban', 'discard', or 'reject'
         * @param {Object|undefined} [kwargs] optional data to pass on
         *  message moderation. This is provided when rejecting the messages
         *  for which title and comment give reason(s) for reject.
         * @param {string} [kwargs.title]
         * @param {string} [kwargs.comment]
         */
        async moderate(decision, kwargs) {
            await this.async(() => this.constructor.moderate([this], decision, kwargs));
        }

        /**
         * Opens the view that allows to resend the message in case of failure.
         */
        openResendAction() {
            this.env.bus.trigger('do-action', {
                action: 'mail.mail_resend_message_action',
                options: {
                    additional_context: {
                        mail_message_to_resend: this.__mfield_id(this),
                    },
                },
            });
        }

        /**
         * Action to initiate reply to current message in Discuss Inbox. Assumes
         * that Discuss and Inbox are already opened.
         */
        replyTo() {
            this.env.messaging.__mfield_discuss(this).replyToMessage(this);
        }

        /**
         * Toggle check state of this message in the context of the provided
         * thread and its stringifiedDomain.
         *
         * @param {mail.thread} thread
         * @param {string} threadStringifiedDomain
         */
        toggleCheck(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            if (threadCache.__mfield_checkedMessages(this).includes(this)) {
                threadCache.update({
                    __mfield_checkedMessages: [['unlink', this]],
                });
            } else {
                threadCache.update({
                    __mfield_checkedMessages: [['link', this]],
                });
            }
        }

        /**
         * Toggle the starred status of the provided message.
         */
        async toggleStar() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[this.__mfield_id(this)]]
            }));
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @returns {boolean}
         */
        _computeFailureNotifications() {
            return [['replace', this.__mfield_notifications(this).filter(notifications =>
                ['exception', 'bounce'].includes(notifications.__mfield_notification_status(this))
            )]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCheckbox() {
            return this.__mfield_isModeratedByCurrentPartner(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAuthor() {
            return !!(
                this.__mfield_author(this) &&
                this.__mfield_messagingCurrentPartner(this) &&
                this.__mfield_messagingCurrentPartner(this) === this.__mfield_author(this)
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsBodyEqualSubtypeDescription() {
            if (!this.__mfield_body(this) || !this.__mfield_subtype_description(this)) {
                return false;
            }
            const inlineBody = htmlToTextContentInline(this.__mfield_body(this));
            return inlineBody.toLowerCase() === this.__mfield_subtype_description(this).toLowerCase();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsModeratedByCurrentPartner() {
            return (
                this.__mfield_moderation_status(this) === 'pending_moderation' &&
                this.__mfield_originThread(this) &&
                this.__mfield_originThread(this).__mfield_isModeratedByCurrentPartner(this)
            );
        }

        /**
         * @private
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return [['link', this.env.messaging]];
        }

        /**
         * @private
         * @returns {mail.thread[]}
         */
        _computeNonOriginThreads() {
            const nonOriginThreads = this.__mfield_serverChannels(this).filter(thread => thread !== this.__mfield_originThread(this));
            if (this.__mfield_isHistory(this)) {
                nonOriginThreads.push(this.env.messaging.__mfield_history(this));
            }
            if (this.__mfield_isNeedaction(this)) {
                nonOriginThreads.push(this.env.messaging.__mfield_inbox(this));
            }
            if (this.__mfield_isStarred(this)) {
                nonOriginThreads.push(this.env.messaging.__mfield_starred(this));
            }
            if (this.env.messaging.__mfield_moderation(this) && this.__mfield_isModeratedByCurrentPartner(this)) {
                nonOriginThreads.push(this.env.messaging.__mfield_moderation(this));
            }
            return [['replace', nonOriginThreads]];
        }

        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         *
         * @private
         * @returns {string}
         */
        _computePrettyBody() {
            let prettyBody;
            for (const emoji of emojis) {
                const { unicode } = emoji;
                const regexp = new RegExp(
                    `(?:^|\\s|<[a-z]*>)(${unicode})(?=\\s|$|</[a-z]*>)`,
                    "g"
                );
                const originalBody = this.__mfield_body(this);
                prettyBody = this.__mfield_body(this).replace(
                    regexp,
                    ` <span class="o_mail_emoji">${unicode}</span> `
                );
                // Idiot-proof limit. If the user had the amazing idea of
                // copy-pasting thousands of emojis, the image rendering can lead
                // to memory overflow errors on some browsers (e.g. Chrome). Set an
                // arbitrary limit to 200 from which we simply don't replace them
                // (anyway, they are already replaced by the unicode counterpart).
                if (_.str.count(prettyBody, "o_mail_emoji") > 200) {
                    prettyBody = originalBody;
                }
            }
            // add anchor tags to urls
            return parseAndTransform(prettyBody, addLink);
        }

        /**
         * @private
         * @returns {mail.thread[]}
         */
        _computeThreads() {
            const threads = [...this.__mfield_nonOriginThreads(this)];
            if (this.__mfield_originThread(this)) {
                threads.push(this.__mfield_originThread(this));
            }
            return [['replace', threads]];
        }

    }

    Message.fields = {
        __mfield_attachments: many2many('mail.attachment', {
            inverse: '__mfield_messages',
        }),
        __mfield_author: many2one('mail.partner', {
            inverse: '__mfield_messagesAsAuthor',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        __mfield_body: attr({
            default: "",
        }),
        __mfield_checkedThreadCaches: many2many('mail.thread_cache', {
            inverse: '__mfield_checkedMessages',
        }),
        __mfield_date: attr({
            default: moment(),
        }),
        __mfield_email_from: attr(),
        __mfield_failureNotifications: one2many('mail.notification', {
            compute: '_computeFailureNotifications',
            dependencies: [
                '__mfield_notificationsStatus',
            ],
        }),
        __mfield_hasCheckbox: attr({
            compute: '_computeHasCheckbox',
            default: false,
            dependencies: [
                '__mfield_isModeratedByCurrentPartner',
            ],
        }),
        __mfield_id: attr(),
        __mfield_isCurrentPartnerAuthor: attr({
            compute: '_computeIsCurrentPartnerAuthor',
            default: false,
            dependencies: [
                '__mfield_author',
                '__mfield_messagingCurrentPartner',
            ],
        }),
        /**
         * States whether `body` and `subtype_description` contain similar
         * values.
         *
         * This is necessary to avoid displaying both of them together when they
         * contain duplicate information. This will especially happen with
         * messages that are posted automatically at the creation of a record
         * (messages that serve as tracking messages). They do have hard-coded
         * "record created" body while being assigned a subtype with a
         * description that states the same information.
         *
         * Fixing newer messages is possible by not assigning them a duplicate
         * body content, but the check here is still necessary to handle
         * existing messages.
         *
         * Limitations:
         * - A translated subtype description might not match a non-translatable
         *   body created by a user with a different language.
         * - Their content might be mostly but not exactly the same.
         */
        __mfield_isBodyEqualSubtypeDescription: attr({
            compute: '_computeIsBodyEqualSubtypeDescription',
            default: false,
            dependencies: [
                '__mfield_body',
                '__mfield_subtype_description',
            ],
        }),
        __mfield_isModeratedByCurrentPartner: attr({
            compute: '_computeIsModeratedByCurrentPartner',
            default: false,
            dependencies: [
                '__mfield_moderation_status',
                '__mfield_originThread',
                '__mfield_originThreadIsModeratedByCurrentPartner',
            ],
        }),
        __mfield_isTemporary: attr({
            default: false,
        }),
        __mfield_isTransient: attr({
            default: false,
        }),
        __mfield_is_discussion: attr({
            default: false,
        }),
        /**
         * Determine whether the message was a needaction. Useful to make it
         * present in history mailbox.
         */
        __mfield_isHistory: attr({
            default: false,
        }),
        /**
         * Determine whether the message is needaction. Useful to make it
         * present in inbox mailbox and messaging menu.
         */
        __mfield_isNeedaction: attr({
            default: false,
        }),
        __mfield_is_note: attr({
            default: false,
        }),
        __mfield_is_notification: attr({
            default: false,
        }),
        /**
         * Determine whether the message is starred. Useful to make it present
         * in starred mailbox.
         */
        __mfield_isStarred: attr({
            default: false,
        }),
        __mfield_message_type: attr(),
        __mfield_messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        __mfield_messagingCurrentPartner: many2one('mail.partner', {
            related: '__mfield_messaging.__mfield_currentPartner',
        }),
        __mfield_messagingHistory: many2one('mail.thread', {
            related: '__mfield_messaging.__mfield_history',
        }),
        __mfield_messagingInbox: many2one('mail.thread', {
            related: '__mfield_messaging.__mfield_inbox',
        }),
        __mfield_messagingModeration: many2one('mail.thread', {
            related: '__mfield_messaging.__mfield_moderation',
        }),
        __mfield_messagingStarred: many2one('mail.thread', {
            related: '__mfield_messaging.__mfield_starred',
        }),
        __mfield_moderation_status: attr(),
        /**
         * List of non-origin threads that this message is linked to. This field
         * is read-only.
         */
        __mfield_nonOriginThreads: many2many('mail.thread', {
            compute: '_computeNonOriginThreads',
            dependencies: [
                '__mfield_isHistory',
                '__mfield_isModeratedByCurrentPartner',
                '__mfield_isNeedaction',
                '__mfield_isStarred',
                '__mfield_messagingHistory',
                '__mfield_messagingInbox',
                '__mfield_messagingModeration',
                '__mfield_messagingStarred',
                '__mfield_originThread',
                '__mfield_serverChannels',
            ],
        }),
        __mfield_notifications: one2many('mail.notification', {
            inverse: '__mfield_message',
            isCausal: true,
        }),
        __mfield_notificationsStatus: attr({
            default: [],
            related: '__mfield_notifications.__mfield_notification_status',
        }),
        /**
         * Origin thread of this message (if any).
         */
        __mfield_originThread: many2one('mail.thread'),
        __mfield_originThreadIsModeratedByCurrentPartner: attr({
            default: false,
            related: '__mfield_originThread.__mfield_isModeratedByCurrentPartner',
        }),
        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        __mfield_prettyBody: attr({
            compute: '_computePrettyBody',
            dependencies: [
                '__mfield_body',
            ],
        }),
        __mfield_subject: attr(),
        __mfield_subtype_description: attr(),
        __mfield_subtype_id: attr(),
        /**
         * All threads that this message is linked to. This field is read-only.
         */
        __mfield_threads: many2many('mail.thread', {
            compute: '_computeThreads',
            dependencies: [
                '__mfield_originThread',
                '__mfield_nonOriginThreads',
            ],
            inverse: '__mfield_messages',
        }),
        __mfield_tracking_value_ids: attr({
            default: [],
        }),
        /**
         * All channels containing this message on the server.
         * Equivalent of python field `channel_ids`.
         */
        __mfield_serverChannels: many2many('mail.thread', {
            inverse: '__mfield_messagesAsServerChannel',
        }),
    };

    Message.modelName = 'mail.message';

    return Message;
}

registerNewModel('mail.message', factory);

});
