odoo.define('mail.messaging.entity.Message', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewEntity } = require('mail.messaging.entity.core');
const { addLink, parseAndTransform } = require('mail.utils');

const { str_to_datetime } = require('web.time');

function MessageFactory({ Entity }) {

    class Message extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {mail.messaging.entity.Thread} thread
         * @param {string} threadStringifiedDomain
         */
        static checkAll(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            threadCache.link({ checkedMessages: threadCache.messages });
        }

        /**
         * Mark all messages of current user with given domain as read.
         *
         * @static
         * @param {Array[]} domain
         */
        static async markAllAsRead(domain) {
            await this.env.rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: { domain },
            });
        }

        /**
         * Applies the moderation `decision` on the provided messages.
         *
         * @static
         * @param {mail.messaging.entity.Message} messages
         * @param {string} decision: 'accept', 'allow', ban', 'discard', or 'reject'
         * @param {Object|undefined} [kwargs] optional data to pass on
         *  message moderation. This is provided when rejecting the messages
         *  for which title and comment give reason(s) for reject.
         * @param {string} [kwargs.title]
         * @param {string} [kwargs.comment]
         */
        static async moderate(messages, decision, kwargs) {
            const messageIds = messages.map(message => message.id);
            await this.env.rpc({
                model: 'mail.message',
                method: 'moderate',
                args: [messageIds, decision],
                kwargs: kwargs,
            });
        }

        /**
         * @static
         * @param {mail.messaging.entity.Thread} thread
         * @param {string} threadStringifiedDomain
         */
        static uncheckAll(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            threadCache.unlink({ checkedMessages: threadCache.messages });
        }

        /**
         * Unstar all starred messages of current user.
         */
        static async unstarAll() {
            await this.env.rpc({
                model: 'mail.message',
                method: 'unstar_all',
            });
        }

        /**
         * @returns {mail.messaging.entity.Thread[]}
         */
        get allThreads() {
            const threads = this.threadCaches.map(cache => cache.thread);
            let allThreads = threads;
            if (this.originThread) {
                allThreads = allThreads.concat([this.originThread]);
            }
            return [...new Set(allThreads)];
        }

        /**
         * @returns {boolean}
         */
        get hasCheckbox() {
            return this.isModeratedByUser;
        }

        /**
         * @param {mail.messaging.entity.Thread} thread
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
         * @returns {boolean}
         */
        get isModeratedByUser() {
            return (
                this.moderation_status === 'pending_moderation' &&
                this.originThread &&
                this.originThread.isModeratedByUser
            );
        }

        /**
         * Mark this message as read, so that it no longer appears in current
         * partner Inbox.
         */
        async markAsRead() {
            await this.env.rpc({
                model: 'mail.message',
                method: 'set_message_done',
                args: [[this.id]]
            });
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
            await this.constructor.moderate([this], decision, kwargs);
        }

        /**
         * @returns {string}
         */
        get prettyBody() {
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
         * Action to initiate reply to given message.
         */
        replyTo() {
            const discuss = this.env.messaging.discuss;
            if (!discuss.isOpen) {
                return;
            }
            if (discuss.replyingToMessage === this) {
                discuss.clearReplyingToMessage();
            } else {
                discuss.link({ replyingToMessage: this });
            }
        }

        /**
         * Toggle check state of this message in the context of the provided
         * thread and its stringifiedDomain.
         *
         * @param {mail.messaging.entity.Thread} thread
         * @param {string} threadStringifiedDomain
         */
        toggleCheck(thread, threadStringifiedDomain) {
            const threadCache = thread.cache(threadStringifiedDomain);
            if (threadCache.checkedMessages.includes(this)) {
                threadCache.unlink({ checkedMessages: this });
            } else {
                threadCache.link({ checkedMessages: this });
            }
        }

        /**
         * Toggle the starred status of the provided message.
         */
        async toggleStar() {
            await this.env.rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[this.id]]
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _createInstanceLocalId(data) {
            return `${this.constructor.localId}_${data.id}`;
        }

        /**
         * @override
         */
        _update(data) {
            const {
                attachment_ids,
                author_id, author_id: [
                    authorId,
                    authorDisplayName
                ] = [],
                body = this.body || "",
                channel_ids,
                customer_email_data = this.customer_email_data,
                customer_email_status = this.customer_email_status,
                date,
                email_from = this.email_from,
                history_partner_ids,
                id = this.id,
                isTransient = this.isTransient || false,
                is_discussion = this.is_discussion || false,
                is_note = this.is_note || false,
                is_notification = this.is_notification || false,
                message_type = this.message_type,
                model,
                moderation_status = this.moderation_status,
                module_icon = this.module_icon,
                needaction_partner_ids,
                record_name,
                res_id,
                snailmail_error = this.snailmail_error,
                snailmail_status = this.snailmail_status,
                starred_partner_ids,
                subject = this.subject,
                subtype_description = this.subtype_description,
                subtype_id = this.subtype_id,
                tracking_value_ids = this.tracking_value_ids || [],
            } = data;

            this._write({
                body,
                customer_email_data,
                customer_email_status,
                date: date
                    ? moment(str_to_datetime(date))
                    : this.date
                        ? this.date
                        : moment(),
                email_from,
                id,
                isTransient,
                is_discussion,
                is_note,
                is_notification,
                message_type,
                model: 'mail.message',
                moderation_status,
                module_icon,
                needaction_partner_ids,
                snailmail_error,
                snailmail_status,
                subject,
                subtype_description,
                subtype_id,
                tracking_value_ids,
            });

            // attachments
            if (attachment_ids) {
                const prevAttachments = this.attachments;
                const newAttachments = [];
                for (const attachmentData of attachment_ids) {
                    const attachment = this.env.entities.Attachment.insert(attachmentData);
                    this.link({ attachments: attachment });
                    newAttachments.push(attachment);
                }
                const oldPrevAttachments = prevAttachments.filter(
                    attachment => !newAttachments.includes(attachment.localId)
                );
                for (const oldPrevAttachment of oldPrevAttachments) {
                    this.unlink({ attachments: oldPrevAttachment });
                }
            }
            // author
            if (author_id) {
                const newAuthor = this.env.entities.Partner.insert({
                    display_name: authorDisplayName,
                    id: authorId,
                });
                const prevAuthor = this.author;
                if (newAuthor !== prevAuthor) {
                    this.link({ author: newAuthor });
                }
            }
            // originThread
            if (model && res_id) {
                let newOriginThread = this.env.entities.Thread.fromModelAndId({
                    id: res_id,
                    model,
                });
                if (!newOriginThread) {
                    newOriginThread = this.env.entities.Thread.create({
                        id: res_id,
                        model,
                    });
                }
                if (record_name) {
                    newOriginThread.update({ name: record_name });
                }
                const prevOriginThread = this.originThread;
                if (newOriginThread !== prevOriginThread) {
                    this.link({ originThread: newOriginThread });
                }
            }
            // threads
            const currentPartner = this.env.messaging.currentPartner;
            const inboxMailbox = this.env.entities.Thread.mailboxFromId('inbox');
            const starredMailbox = this.env.entities.Thread.mailboxFromId('starred');
            const historyMailbox = this.env.entities.Thread.mailboxFromId('history');
            const moderationMailbox = this.env.entities.Thread.mailboxFromId('moderation');
            if (needaction_partner_ids) {
                if (needaction_partner_ids.includes(currentPartner.id)) {
                    this.link({ threadCaches: inboxMailbox.mainCache });
                } else {
                    this.unlink({ threadCaches: inboxMailbox.mainCache });
                }
            }
            if (starred_partner_ids) {
                if (starred_partner_ids.includes(currentPartner.id)) {
                    this.link({ threadCaches: starredMailbox.mainCache });
                } else {
                    this.unlink({ threadCaches: starredMailbox.mainCache });
                }
            }
            if (history_partner_ids) {
                if (history_partner_ids.includes(currentPartner.id)) {
                    this.link({ threadCaches: historyMailbox.mainCache });
                } else {
                    this.unlink({ threadCaches: historyMailbox.mainCache });
                }
            }
            if (moderationMailbox && this.moderation_status !== 'pending') {
                this.unlink({ threadCaches: moderationMailbox.mainCache });
            }
            if (channel_ids) {
                const prevChannels = this.allThreads.filter(
                    thread => thread.model === 'mail.channel'
                );
                const newChannels = [];
                for (const channelId of channel_ids) {
                    let channel = this.env.entities.Thread.channelFromId(channelId);
                    if (!channel) {
                        channel = this.env.entities.Thread.create({
                            id: channelId,
                            model: 'mail.channel',
                        });
                    }
                    this.link({ threadCaches: channel.mainCache });
                    newChannels.push(channel);
                }
                const oldPrevChannels = prevChannels.filter(
                    channel => !newChannels.includes(channel)
                );
                for (const channel of oldPrevChannels) {
                    for (const cache of channel.caches) {
                        this.unlink({ threadCaches: cache });
                    }
                }
            }
        }

    }

    Object.assign(Message, {
        relations: Object.assign({}, Entity.relations, {
            attachments: {
                inverse: 'messages',
                to: 'Attachment',
                type: 'many2many',
            },
            author: {
                inverse: 'authorMessages',
                to: 'Partner',
                type: 'many2one',
            },
            checkedThreadCaches: {
                inverse: 'checkedMessages',
                to: 'ThreadCache',
                type: 'many2many',
            },
            originThread: {
                inverse: 'originThreadMessages',
                to: 'Thread',
                type: 'many2one',
            },
            replyingToDiscuss: {
                inverse: 'replyingToMessage',
                to: 'Discuss',
                type: 'one2one',
            },
            threadCaches: {
                inverse: 'messages',
                to: 'ThreadCache',
                type: 'many2many',
            },
        }),
    });

    return Message;
}

registerNewEntity('Message', MessageFactory);

});
