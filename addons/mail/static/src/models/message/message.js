odoo.define('mail/static/src/models/message/message.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { addLink, htmlToTextContentInline, parseAndTransform, timeFromNow } = require('mail.utils');

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
            threadCache.update({ checkedMessages: [['link', threadCache.messages]] });
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
                    data2.attachments = [['unlink-all']];
                } else {
                    data2.attachments = [
                        ['insert-and-replace', data.attachment_ids.map(attachmentData =>
                            this.env.models['mail.attachment'].convertData(attachmentData)
                        )],
                    ];
                }
            }
            if ('author_id' in data) {
                if (!data.author_id) {
                    data2.author = [['unlink-all']];
                } else if (data.author_id[0] !== 0) {
                    // partner id 0 is a hack of message_format to refer to an
                    // author non-related to a partner. display_name equals
                    // email_from, so this is omitted due to being redundant.
                    data2.author = [
                        ['insert', {
                            display_name: data.author_id[1],
                            id: data.author_id[0],
                        }],
                    ];
                }
            }
            if ('body' in data) {
                data2.body = data.body;
            }
            if ('channel_ids' in data && data.channel_ids) {
                const channels = data.channel_ids
                    .map(channelId =>
                        this.env.models['mail.thread'].findFromIdentifyingData({
                            id: channelId,
                            model: 'mail.channel',
                        })
                    ).filter(channel => !!channel);
                data2.serverChannels = [['replace', channels]];
            }
            if ('date' in data && data.date) {
                data2.date = moment(str_to_datetime(data.date));
            }
            if ('email_from' in data) {
                data2.email_from = data.email_from;
            }
            if ('history_partner_ids' in data) {
                data2.isHistory = data.history_partner_ids.includes(this.env.messaging.currentPartner.id);
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('is_discussion' in data) {
                data2.is_discussion = data.is_discussion;
            }
            if ('is_note' in data) {
                data2.is_note = data.is_note;
            }
            if ('is_notification' in data) {
                data2.is_notification = data.is_notification;
            }
            if ('message_type' in data) {
                data2.message_type = data.message_type;
            }
            if ('model' in data && 'res_id' in data && data.model && data.res_id) {
                const originThreadData = {
                    id: data.res_id,
                    model: data.model,
                };
                if ('record_name' in data && data.record_name) {
                    originThreadData.name = data.record_name;
                }
                if ('res_model_name' in data && data.res_model_name) {
                    originThreadData.model_name = data.res_model_name;
                }
                if ('module_icon' in data) {
                    originThreadData.moduleIcon = data.module_icon;
                }
                data2.originThread = [['insert', originThreadData]];
            }
            if ('moderation_status' in data) {
                data2.moderation_status = data.moderation_status;
            }
            if ('needaction_partner_ids' in data) {
                data2.isNeedaction = data.needaction_partner_ids.includes(this.env.messaging.currentPartner.id);
            }
            if ('notifications' in data) {
                data2.notifications = [['insert', data.notifications.map(notificationData =>
                    this.env.models['mail.notification'].convertData(notificationData)
                )]];
            }
            if ('starred_partner_ids' in data) {
                data2.isStarred = data.starred_partner_ids.includes(this.env.messaging.currentPartner.id);
            }
            if ('subject' in data) {
                data2.subject = data.subject;
            }
            if ('subtype_description' in data) {
                data2.subtype_description = data.subtype_description;
            }
            if ('subtype_id' in data) {
                data2.subtype_id = data.subtype_id;
            }
            if ('tracking_value_ids' in data) {
                data2.tracking_value_ids = data.tracking_value_ids;
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
                args: [messages.map(message => message.id)]
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
            const messageIds = messages.map(message => message.id);
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
                for (const thread of message.threads) {
                    if (thread.model !== 'mail.channel' || thread.channel_type === 'channel') {
                        // disabled on non-channel threads and
                        // on `channel` channels for performance reasons
                        continue;
                    }
                    this.env.models['mail.message_seen_indicator'].insert({
                        channelId: thread.id,
                        messageId: message.id,
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
            threadCache.update({ checkedMessages: [['unlink', threadCache.messages]] });
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
            const relatedCheckedThreadCache = this.checkedThreadCaches.find(
                threadCache => (
                    threadCache.thread === thread &&
                    threadCache.stringifiedDomain === threadStringifiedDomain
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
                args: [[this.id]]
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
                        mail_message_to_resend: this.id,
                    },
                },
            });
        }

        /**
         * Refreshes the value of `dateFromNow` field to the "current now".
         */
        refreshDateFromNow() {
            this.update({ dateFromNow: this._computeDateFromNow() });
        }

        /**
         * Action to initiate reply to current message in Discuss Inbox. Assumes
         * that Discuss and Inbox are already opened.
         */
        replyTo() {
            this.env.messaging.discuss.replyToMessage(this);
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
            if (threadCache.checkedMessages.includes(this)) {
                threadCache.update({ checkedMessages: [['unlink', this]] });
            } else {
                threadCache.update({ checkedMessages: [['link', this]] });
            }
        }

        /**
         * Toggle the starred status of the provided message.
         */
        async toggleStar() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[this.id]]
            }));
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @returns {string}
         */
        _computeDateFromNow() {
            if (!this.date) {
                return clear();
            }
            return timeFromNow(this.date);
        }

        /**
         * @returns {boolean}
         */
        _computeFailureNotifications() {
            return [['replace', this.notifications.filter(notifications =>
                ['exception', 'bounce'].includes(notifications.notification_status)
            )]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCheckbox() {
            return this.isModeratedByCurrentPartner;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAuthor() {
            return !!(
                this.author &&
                this.messagingCurrentPartner &&
                this.messagingCurrentPartner === this.author
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsBodyEqualSubtypeDescription() {
            if (!this.body || !this.subtype_description) {
                return false;
            }
            const inlineBody = htmlToTextContentInline(this.body);
            return inlineBody.toLowerCase() === this.subtype_description.toLowerCase();
        }

        /**
         * The method does not attempt to cover all possible cases of empty
         * messages, but mostly those that happen with a standard flow. Indeed
         * it is preferable to be defensive and show an empty message sometimes
         * instead of hiding a non-empty message.
         *
         * The main use case for when a message should become empty is for a
         * message posted with only an attachment (no body) and then the
         * attachment is deleted.
         *
         * The main use case for being defensive with the check is when
         * receiving a message that has no textual content but has other
         * meaningful HTML tags (eg. just an <img/>).
         *
         * @private
         * @returns {boolean}
         */
        _computeIsEmpty() {
            const isBodyEmpty = (
                !this.body ||
                [
                    '',
                    '<p></p>',
                    '<p><br></p>',
                    '<p><br/></p>',
                ].includes(this.body.replace(/\s/g, ''))
            );
            return (
                isBodyEmpty &&
                this.attachments.length === 0 &&
                this.tracking_value_ids.length === 0 &&
                !this.subtype_description
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsModeratedByCurrentPartner() {
            return (
                this.moderation_status === 'pending_moderation' &&
                this.originThread &&
                this.originThread.isModeratedByCurrentPartner
            );
        }
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsSubjectSimilarToOriginThreadName() {
            if (
                !this.subject ||
                !this.originThread ||
                !this.originThread.name
            ) {
                return false;
            }
            const threadName = this.originThread.name.toLowerCase().trim();
            const prefixList = ['re:', 'fw:', 'fwd:'];
            let cleanedSubject = this.subject.toLowerCase();
            let wasSubjectCleaned = true;
            while (wasSubjectCleaned) {
                wasSubjectCleaned = false;
                if (threadName === cleanedSubject) {
                    return true;
                }
                for (const prefix of prefixList) {
                    if (cleanedSubject.startsWith(prefix)) {
                        cleanedSubject = cleanedSubject.replace(prefix, '').trim();
                        wasSubjectCleaned = true;
                        break;
                    }
                }
            }
            return false;
        }

        /**
         * @private
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return [['link', this.env.messaging]];
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
            if (!this.body) {
                // body null in db, body will be false instead of empty string
                return clear();
            }
            let prettyBody;
            for (const emoji of emojis) {
                const { unicode } = emoji;
                const regexp = new RegExp(
                    `(?:^|\\s|<[a-z]*>)(${unicode})(?=\\s|$|</[a-z]*>)`,
                    "g"
                );
                const originalBody = this.body;
                prettyBody = this.body.replace(
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
            const threads = [...this.serverChannels];
            if (this.isHistory) {
                threads.push(this.env.messaging.history);
            }
            if (this.isNeedaction) {
                threads.push(this.env.messaging.inbox);
            }
            if (this.isStarred) {
                threads.push(this.env.messaging.starred);
            }
            if (this.env.messaging.moderation && this.isModeratedByCurrentPartner) {
                threads.push(this.env.messaging.moderation);
            }
            if (this.originThread) {
                threads.push(this.originThread);
            }
            return [['replace', threads]];
        }

    }

    Message.fields = {
        attachments: many2many('mail.attachment', {
            inverse: 'messages',
        }),
        author: many2one('mail.partner', {
            inverse: 'messagesAsAuthor',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        body: attr({
            default: "",
        }),
        checkedThreadCaches: many2many('mail.thread_cache', {
            inverse: 'checkedMessages',
        }),
        /**
         * Determines the date of the message as a moment object.
         */
        date: attr(),
        /**
         * States the time elapsed since date up to now.
         */
        dateFromNow: attr({
            compute: '_computeDateFromNow',
            dependencies: [
                'date',
            ],
        }),
        email_from: attr(),
        failureNotifications: one2many('mail.notification', {
            compute: '_computeFailureNotifications',
            dependencies: ['notificationsStatus'],
        }),
        hasCheckbox: attr({
            compute: '_computeHasCheckbox',
            default: false,
            dependencies: ['isModeratedByCurrentPartner'],
        }),
        id: attr(),
        isCurrentPartnerAuthor: attr({
            compute: '_computeIsCurrentPartnerAuthor',
            default: false,
            dependencies: [
                'author',
                'messagingCurrentPartner',
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
        isBodyEqualSubtypeDescription: attr({
            compute: '_computeIsBodyEqualSubtypeDescription',
            default: false,
            dependencies: [
                'body',
                'subtype_description',
            ],
        }),
        /**
         * Determine whether the message has to be considered empty or not.
         *
         * An empty message has no text, no attachment and no tracking value.
         */
        isEmpty: attr({
            compute: '_computeIsEmpty',
            dependencies: [
                'attachments',
                'body',
                'subtype_description',
                'tracking_value_ids',
            ],
        }),
        isModeratedByCurrentPartner: attr({
            compute: '_computeIsModeratedByCurrentPartner',
            default: false,
            dependencies: [
                'moderation_status',
                'originThread',
                'originThreadIsModeratedByCurrentPartner',
            ],
        }),
        /**
         * States whether `originThread.name` and `subject` contain similar
         * values except it contains the extra prefix at the start
         * of the subject.
         *
         * This is necessary to avoid displaying the subject, if
         * the subject is same as threadname.
         */
        isSubjectSimilarToOriginThreadName: attr({
            compute: '_computeIsSubjectSimilarToOriginThreadName',
            dependencies: [
                'originThread',
                'originThreadName',
                'subject',
            ],
        }),
        isTemporary: attr({
            default: false,
        }),
        isTransient: attr({
            default: false,
        }),
        is_discussion: attr({
            default: false,
        }),
        /**
         * Determine whether the message was a needaction. Useful to make it
         * present in history mailbox.
         */
        isHistory: attr({
            default: false,
        }),
        /**
         * Determine whether the message is needaction. Useful to make it
         * present in inbox mailbox and messaging menu.
         */
        isNeedaction: attr({
            default: false,
        }),
        is_note: attr({
            default: false,
        }),
        is_notification: attr({
            default: false,
        }),
        /**
         * Determine whether the message is starred. Useful to make it present
         * in starred mailbox.
         */
        isStarred: attr({
            default: false,
        }),
        message_type: attr(),
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        messagingCurrentPartner: many2one('mail.partner', {
            related: 'messaging.currentPartner',
        }),
        messagingHistory: many2one('mail.thread', {
            related: 'messaging.history',
        }),
        messagingInbox: many2one('mail.thread', {
            related: 'messaging.inbox',
        }),
        messagingModeration: many2one('mail.thread', {
            related: 'messaging.moderation',
        }),
        messagingStarred: many2one('mail.thread', {
            related: 'messaging.starred',
        }),
        moderation_status: attr(),
        notifications: one2many('mail.notification', {
            inverse: 'message',
            isCausal: true,
        }),
        notificationsStatus: attr({
            default: [],
            related: 'notifications.notification_status',
        }),
        /**
         * Origin thread of this message (if any).
         */
        originThread: many2one('mail.thread', {
            inverse: 'messagesAsOriginThread',
        }),
        originThreadIsModeratedByCurrentPartner: attr({
            default: false,
            related: 'originThread.isModeratedByCurrentPartner',
        }),
        /**
         * Serves as compute dependency for isSubjectSimilarToOriginThreadName
         */
        originThreadName: attr({
            related: 'originThread.name',
        }),
        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        prettyBody: attr({
            compute: '_computePrettyBody',
            default: "",
            dependencies: ['body'],
        }),
        subject: attr(),
        subtype_description: attr(),
        subtype_id: attr(),
        /**
         * All threads that this message is linked to. This field is read-only.
         */
        threads: many2many('mail.thread', {
            compute: '_computeThreads',
            dependencies: [
                'isHistory',
                'isModeratedByCurrentPartner',
                'isNeedaction',
                'isStarred',
                'messagingHistory',
                'messagingInbox',
                'messagingModeration',
                'messagingStarred',
                'originThread',
                'serverChannels',
            ],
            inverse: 'messages',
        }),
        tracking_value_ids: attr({
            default: [],
        }),
        /**
         * All channels containing this message on the server.
         * Equivalent of python field `channel_ids`.
         */
        serverChannels: many2many('mail.thread', {
            inverse: 'messagesAsServerChannel',
        }),
    };

    Message.modelName = 'mail.message';

    return Message;
}

registerNewModel('mail.message', factory);

});
