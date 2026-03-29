/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, replace, unlinkAll } from '@mail/model/model_field_command';
import emojis from '@mail/js/emojis';
import { addLink, htmlToTextContentInline, parseAndTransform, timeFromNow } from '@mail/js/utils';

import { session } from '@web/session';

import { str_to_datetime } from 'web.time';

function factory(dependencies) {

    class Message extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('attachment_ids' in data) {
                if (!data.attachment_ids) {
                    data2.attachments = unlinkAll();
                } else {
                    data2.attachments = insertAndReplace(data.attachment_ids.map(attachmentData =>
                        this.messaging.models['mail.attachment'].convertData(attachmentData)
                    ));
                }
            }
            if ('author_id' in data) {
                if (!data.author_id) {
                    data2.author = unlinkAll();
                } else if (data.author_id[0] !== 0) {
                    // partner id 0 is a hack of message_format to refer to an
                    // author non-related to a partner. display_name equals
                    // email_from, so this is omitted due to being redundant.
                    data2.author = insert({
                        display_name: data.author_id[1],
                        id: data.author_id[0],
                    });
                }
            }
            if ('body' in data) {
                data2.body = data.body;
            }
            if ('date' in data && data.date) {
                data2.date = moment(str_to_datetime(data.date));
            }
            if ('email_from' in data) {
                data2.email_from = data.email_from;
            }
            if ('guestAuthor' in data) {
                data2.guestAuthor = data.guestAuthor;
            }
            if ('history_partner_ids' in data && this.messaging.currentPartner) {
                data2.isHistory = data.history_partner_ids.includes(this.messaging.currentPartner.id);
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
            if ('messageReactionGroups' in data) {
                data2.messageReactionGroups = data.messageReactionGroups;
            }
            if ('message_type' in data) {
                data2.message_type = data.message_type;
                data2.is_automated_message = data.message_type === 'auto_message';
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
                data2.originThread = insertAndReplace(originThreadData);
            }
            if ('needaction_partner_ids' in data && this.messaging.currentPartner) {
                data2.isNeedaction = data.needaction_partner_ids.includes(this.messaging.currentPartner.id);
            }
            if ('notifications' in data) {
                data2.notifications = insert(data.notifications.map(notificationData =>
                    this.messaging.models['mail.notification'].convertData(notificationData)
                ));
            }
            if ('parentMessage' in data) {
                if (!data.parentMessage) {
                    data2.parentMessage = clear();
                } else {
                    data2.parentMessage = insertAndReplace(this.convertData(data.parentMessage));
                }
            }
            if ('partner_ids' in data && this.messaging.currentPartner) {
                data2.recipients = insertAndReplace(data.partner_ids.map(partner_id => ({ id: partner_id })));
            }
            if ('recipients' in data) {
                data2.recipients = insertAndReplace(data.recipients);
            }
            if ('starred_partner_ids' in data && this.messaging.currentPartner) {
                data2.isStarred = data.starred_partner_ids.includes(this.messaging.currentPartner.id);
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
         * Performs the given `route` RPC to fetch messages.
         *
         * @static
         * @param {string} route
         * @param {Object} params
         * @returns {mail.message[]}
         */
        static async performRpcMessageFetch(route, params) {
            const messagesData = await this.env.services.rpc({ route, params }, { shadow: true });
            if (!this.messaging) {
                return;
            }
            const messages = this.messaging.models['mail.message'].insert(messagesData.map(
                messageData => this.messaging.models['mail.message'].convertData(messageData)
            ));
            // compute seen indicators (if applicable)
            for (const message of messages) {
                for (const thread of message.threads) {
                    if (thread.model !== 'mail.channel' || thread.channel_type === 'channel') {
                        // disabled on non-channel threads and
                        // on `channel` channels for performance reasons
                        continue;
                    }
                    this.messaging.models['mail.message_seen_indicator'].insert({
                        thread: replace(thread),
                        message: replace(message),
                    });
                }
            }
            return messages;
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
         * Adds the given reaction on this message.
         *
         * @param {string} content
         */
        async addReaction(content) {
            const messageData = await this.env.services.rpc({
                route: '/mail/message/add_reaction',
                params: { content, message_id: this.id },
            });
            if (!this.exists()) {
                return;
            }
            this.update(messageData);
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
         * Removes the given reaction from this message.
         *
         * @param {string} content
         */
        async removeReaction(content) {
            const messageData = await this.env.services.rpc({
                route: '/mail/message/remove_reaction',
                params: { content, message_id: this.id },
            });
            if (!this.exists()) {
                return;
            }
            this.update(messageData);
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

        /**
         * Updates the message's content.
         *
         * @param {Object} param0
         * @param {string} param0.body the new body of the message
         * @param {number[]} param0.attachment_ids
         * @param {string[]} param0.attachment_tokens
         */
        async updateContent({ body, attachment_ids, attachment_tokens }) {
            const messageData = await this.env.services.rpc({
                route: '/mail/message/update_content',
                params: {
                    body,
                    attachment_ids,
                    attachment_tokens,
                    message_id: this.id,
                },
            });
            if (!this.messaging) {
                return;
            }
            this.messaging.models['mail.message'].insert(messageData);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @returns {string|FieldCommand}
         */
        _computeAuthorName() {
            if (this.author) {
                return this.author.nameOrDisplayName;
            }
            if (this.guestAuthor) {
                return this.guestAuthor.name;
            }
            if (this.email_from) {
                return this.email_from;
            }
            return this.env._t("Anonymous");
        }

        /**
         * @returns {boolean}
         */
        _computeCanBeDeleted() {
            if (!session.is_admin && !this.isCurrentUserOrGuestAuthor) {
                return false;
            }
            if (!this.originThread) {
                return false;
            }
            if (this.tracking_value_ids.length > 0) {
                return false;
            }
            if (this.message_type !== 'comment') {
                return false;
            }
            if (this.originThread.model === 'mail.channel') {
                return true;
            }
            return this.is_note;
        }

        /**
         * @returns {boolean}
         */
        _computeCanStarBeToggled() {
            return !this.messaging.isCurrentUserGuest && !this.isTemporary && !this.isTransient;
        }

        /**
         * @returns {string}
         */
        _computeDateDay() {
            if (!this.date) {
                // Without a date, we assume that it's a today message. This is
                // mainly done to avoid flicker inside the UI.
                return this.env._t("Today");
            }
            const date = this.date.format('YYYY-MM-DD');
            if (date === moment().format('YYYY-MM-DD')) {
                return this.env._t("Today");
            } else if (
                date === moment()
                    .subtract(1, 'days')
                    .format('YYYY-MM-DD')
            ) {
                return this.env._t("Yesterday");
            }
            return this.date.format('LL');
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
            return replace(this.notifications.filter(notifications =>
                ['exception', 'bounce'].includes(notifications.notification_status)
            ));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasAttachments() {
            return this.attachments.length > 0;
        }

        /**
         * @returns {boolean}
         */
        _computeHasReactionIcon() {
            return !this.isTemporary && !this.isTransient;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentUserOrGuestAuthor() {
            return !!(
                this.author &&
                this.messaging.currentPartner &&
                this.messaging.currentPartner === this.author
            ) || !!(
                this.guestAuthor &&
                this.messaging.currentGuest &&
                this.messaging.currentGuest === this.guestAuthor
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsBodyEmpty() {
            return (
                !this.body ||
                [
                    '',
                    '<p></p>',
                    '<p><br></p>',
                    '<p><br/></p>',
                ].includes(this.body.replace(/\s/g, ''))
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
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerMentioned() {
            return this.recipients.includes(this.messaging.currentPartner);
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
            return (
                this.isBodyEmpty &&
                !this.hasAttachments &&
                this.tracking_value_ids.length === 0 &&
                !this.subtype_description
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsHighlighted() {
            return (
                this.isCurrentPartnerMentioned &&
                this.originThread &&
                this.originThread.model === 'mail.channel'
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
         * @returns {string}
         */
        _computeMessageTypeText() {
            if (this.message_type === 'notification') {
                return this.env._t("System notification");
            }
            if (this.message_type === "auto_comment") {
                return this.env._t("Automated Targeted Notification");
            }
            if (!this.is_discussion && !this.is_notification) {
                return this.env._t("Note");
            }
            return this.env._t("Message");
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
            const threads = [];
            if (this.isHistory && this.messaging.history) {
                threads.push(this.messaging.history);
            }
            if (this.isNeedaction && this.messaging.inbox) {
                threads.push(this.messaging.inbox);
            }
            if (this.isStarred && this.messaging.starred) {
                threads.push(this.messaging.starred);
            }
            if (this.originThread) {
                threads.push(this.originThread);
            }
            return replace(threads);
        }

    }

    Message.fields = {
        authorName: attr({
            compute: '_computeAuthorName',
        }),
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
        /**
         * Whether this message can be deleted.
         */
        canBeDeleted: attr({
            compute: '_computeCanBeDeleted',
        }),
        /**
         * Whether this message can be starred/unstarred.
         */
        canStarBeToggled: attr({
            compute: '_computeCanStarBeToggled',
        }),
        /**
         * Determines the date of the message as a moment object.
         */
        date: attr(),
        /**
         * States the date of this message as a string (either a relative period
         * in the near past or an actual date for older dates).
         */
        dateDay: attr({
            compute: '_computeDateDay',
        }),
        /**
         * States the time elapsed since date up to now.
         */
        dateFromNow: attr({
            compute: '_computeDateFromNow',
        }),
        email_from: attr(),
        failureNotifications: one2many('mail.notification', {
            compute: '_computeFailureNotifications',
        }),
        guestAuthor: many2one('mail.guest', {
            inverse: 'authoredMessages',
        }),
        /**
         * States whether the message has some attachments.
         */
        hasAttachments: attr({
            compute: '_computeHasAttachments',
        }),
        /**
         * Determines whether the message has a reaction icon.
         */
        hasReactionIcon: attr({
            compute: '_computeHasReactionIcon',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        isCurrentUserOrGuestAuthor: attr({
            compute: '_computeIsCurrentUserOrGuestAuthor',
            default: false,
        }),
        /**
         * States if the body field is empty, regardless of editor default
         * html content. To determine if a message is fully empty, use
         * `isEmpty`.
         */
        isBodyEmpty: attr({
            compute: '_computeIsBodyEmpty',
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
        }),
        /**
         * Determine whether the message has to be considered empty or not.
         *
         * An empty message has no text, no attachment and no tracking value.
         */
        isEmpty: attr({
            compute: '_computeIsEmpty',
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
        }),
        isTemporary: attr({
            default: false,
        }),
        isTransient: attr({
            default: false,
        }),
        is_automated_message: attr({
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
         * Determine whether the current partner is mentioned.
         */
        isCurrentPartnerMentioned: attr({
            compute: '_computeIsCurrentPartnerMentioned',
            default: false,
        }),
        /**
         * Determine whether the message is highlighted.
         */
        isHighlighted: attr({
            compute: '_computeIsHighlighted',
        }),
        /**
         * Determine whether the message is starred. Useful to make it present
         * in starred mailbox.
         */
        isStarred: attr({
            default: false,
        }),
        messageTypeText: attr({
            compute: '_computeMessageTypeText',
        }),
        /**
         * Groups of reactions per content allowing to know the number of
         * reactions for each.
         */
        messageReactionGroups: one2many('mail.message_reaction_group', {
            inverse: 'message',
            isCausal: true,
        }),
        message_type: attr(),
        messageSeenIndicators: one2many('mail.message_seen_indicator', {
            inverse: 'message',
            isCausal: true,
        }),
        /**
         * States the views that are displaying this message.
         */
        messageViews: one2many('mail.message_view', {
            inverse: 'message',
            isCausal: true,
        }),
        notifications: one2many('mail.notification', {
            inverse: 'message',
            isCausal: true,
        }),
        /**
         * Origin thread of this message (if any).
         */
        originThread: many2one('mail.thread', {
            inverse: 'messagesAsOriginThread',
        }),
        /**
         * States the message that this message replies to (if any). Only makes
         * sense on channels. Other types of threads might have a parent message
         * (parent_id in python) that should be ignored for the purpose of this
         * feature.
         */
        parentMessage: many2one('mail.message'),
        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        prettyBody: attr({
            compute: '_computePrettyBody',
            default: "",
        }),
        recipients: many2many('mail.partner'),
        subject: attr(),
        subtype_description: attr(),
        subtype_id: attr(),
        /**
         * All threads that this message is linked to. This field is read-only.
         */
        threads: many2many('mail.thread', {
            compute: '_computeThreads',
            inverse: 'messages',
        }),
        tracking_value_ids: attr({
            default: [],
        }),
    };
    Message.identifyingFields = ['id'];
    Message.modelName = 'mail.message';

    return Message;
}

registerNewModel('mail.message', factory);
