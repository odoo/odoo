/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, create, insert, insertAndReplace, link, replace, unlinkAll } from '@mail/model/model_field_command';
import emojis from '@mail/js/emojis';
import { addLink, htmlToTextContentInline, parseAndTransform, timeFromNow } from '@mail/js/utils';

import { session } from '@web/session';
import { escapeRegExp } from "@web/core/utils/strings"

import { str_to_datetime } from 'web.time';
import { format } from 'web.field_utils';
import { _lt } from 'web.core';

const READ_MORE = _lt("read more");
const READ_LESS = _lt("read less");

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
                data2.originThread = insert(originThreadData);
            }
            if ('needaction_partner_ids' in data && this.messaging.currentPartner) {
                data2.isNeedaction = data.needaction_partner_ids.includes(this.messaging.currentPartner.id);
            }
            if ('notifications' in data) {
                data2.notifications = insert(data.notifications.map(notificationData =>
                    this.messaging.models['mail.notification'].convertData(notificationData)
                ));
            }
            if ('partner_ids' in data && this.messaging.currentPartner) {
                data2.isCurrentPartnerMentioned = data.partner_ids.includes(this.messaging.currentPartner.id);
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
                        channelId: thread.id,
                        messageId: message.id,
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
         * Removes a hash to the map keeping track of open collapsable contents.
         * Basically means it closes it.
         * 
         * @param {String} hash 
         */
        collapseCollapsableContentByHash(hash) {
            const newSet = new Set([...this.currentlyOpenedReadMoreHashes]);
            newSet.delete(hash);
            this.update({ currentlyOpenedReadMoreHashes: newSet });
        }

        /**
         * Adds a hash to the map keeping track of open collapsable contents.
         * Basically means it opens it.
         * 
         * @param {String} hash 
         */
        expandCollapsableContentByHash(hash) {
            this.update({ currentlyOpenedReadMoreHashes: new Set([...this.currentlyOpenedReadMoreHashes.add(hash)]) });
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
         * Performs DOM transformation needed to display the message.
         * It uses a string representation of the DOM as we don't manipulate directly the real DOM with OWL. 
         * 
         * @param {String} content dom string rep on which to apply all the dom maniplation
         * @returns processed content
         */
        processDomTransformation(content, isSafe = false) {
            if (!content) return "";
            if (!isSafe) {
                content = _.escape(content);
            }
            content = this._wrapEmojisForFormatting(content)
            if (this._isThreadCurrentlyBeingSearched()) {
                content = this._highlightBasedOnThreadSearch(content);
            }
            if (this.message_type == 'email') {
                // Only the emails need to have collapsable content for now.
                content = this._insertMoreOrLessTogglersForCollapsableContent(content, true);
            }
            content = parseAndTransform(content, addLink);
            return content;
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
         * Action to initiate reply to current message in Discuss Inbox. Assumes
         * that Discuss and Inbox are already opened.
         */
        replyTo() {
            this.messaging.discuss.replyToMessage(this);
        }

        startEditing() {
            const parser = new DOMParser();
            const htmlDoc = parser.parseFromString(this.body.replaceAll('<br>', '\n').replaceAll('</br>', '\n'), "text/html");
            const textInputContent = htmlDoc.body.textContent;
            const composerData = {
                doFocus: true,
                isLastStateChangeProgrammatic: true,
                textInputCursorStart: textInputContent.length,
                textInputCursorEnd: textInputContent.length,
                textInputSelectionDirection: 'none',
                textInputContent,
            };
            if (this.composerInEditing) {
                this.composerInEditing.update(composerData);
            } else {
                this.messaging.models['mail.composer'].create({
                    messageInEditing: link(this),
                    ...composerData,
                });
            }
            this.update({ isEditing: true });
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
         */
        async updateContent({ body, attachment_ids }) {
            const messageData = await this.env.services.rpc({
                route: '/mail/message/update_content',
                params: {
                    body,
                    attachment_ids,
                    message_id: this.id,
                },
            });
            if (!this.messaging) {
                return;
            }
            this.messaging.models['mail.message'].insert(messageData);
        }
        
        /**
         * @returns {Object}
         */
        get trackingValues() {
            return this.tracking_value_ids.map(trackingValue => {
                const value = Object.assign({}, trackingValue);
                value.changed_field = _.str.sprintf(this.env._t("%s:"), value.changed_field);
                /**
                 * Maps tracked field type to a JS formatter. Tracking values are
                 * not always stored in the same field type as their origin type.
                 * Field types that are not listed here are not supported by
                 * tracking in Python. Also see `create_tracking_values` in Python.
                 */
                switch (value.field_type) {
                    case 'boolean':
                        value.old_value = format.boolean(value.old_value, undefined, { forceString: true });
                        value.new_value = format.boolean(value.new_value, undefined, { forceString: true });
                        break;
                    /**
                     * many2one formatter exists but is expecting id/name_get or data
                     * object but only the target record name is known in this context.
                     *
                     * Selection formatter exists but requires knowing all
                     * possibilities and they are not given in this context.
                     */
                    case 'char':
                    case 'many2one':
                    case 'selection':
                        value.old_value = format.char(value.old_value);
                        value.new_value = format.char(value.new_value);
                        break;
                    case 'date':
                        if (value.old_value) {
                            value.old_value = moment.utc(value.old_value);
                        }
                        if (value.new_value) {
                            value.new_value = moment.utc(value.new_value);
                        }
                        value.old_value = format.date(value.old_value);
                        value.new_value = format.date(value.new_value);
                        break;
                    case 'datetime':
                        if (value.old_value) {
                            value.old_value = moment.utc(value.old_value);
                        }
                        if (value.new_value) {
                            value.new_value = moment.utc(value.new_value);
                        }
                        value.old_value = format.datetime(value.old_value);
                        value.new_value = format.datetime(value.new_value);
                        break;
                    case 'float':
                        value.old_value = format.float(value.old_value);
                        value.new_value = format.float(value.new_value);
                        break;
                    case 'integer':
                        value.old_value = format.integer(value.old_value);
                        value.new_value = format.integer(value.new_value);
                        break;
                    case 'monetary':
                        value.old_value = format.monetary(value.old_value, undefined, {
                            currency: value.currency_id
                                ? this.env.session.currencies[value.currency_id]
                                : undefined,
                            forceString: true,
                        });
                        value.new_value = format.monetary(value.new_value, undefined, {
                            currency: value.currency_id
                                ? this.env.session.currencies[value.currency_id]
                                : undefined,
                            forceString: true,
                        });
                        break;
                    case 'text':
                        value.old_value = format.text(value.old_value);
                        value.new_value = format.text(value.new_value);
                        break;
                }
                return value;
            });
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
            if (this.originThread.model === 'mail.channel') {
                return this.message_type === 'comment';
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
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         *
         * @private
         * @returns {string}
         */
        _computePrettyBody() {
            return this.processDomTransformation(this.body, true);
        }
        _computePrettyAuthor() {
            if (!this.author) {
                return this.processDomTransformation("");
            }
            return this.processDomTransformation(this.author.nameOrDisplayName);
        }
        _computePrettySubject() {
            return this.processDomTransformation(this.subject);
        }
        _computePrettySubtypeDescription() {
            return this.processDomTransformation(this.subtype_description);
        }
        _computePrettyTrackingValues() {
            return Object.fromEntries(this.trackingValues.map(({id, new_value, old_value, changed_field}) =>
                [
                    id,
                    {
                        'new': this.processDomTransformation(new_value),
                        'old': this.processDomTransformation(old_value),
                        'changed_field': this.processDomTransformation(changed_field),
                    }
                ]
            ));
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

        /**
         * Apllies the hightlighting based the thread search text. 
         * 
         * @private
         * @param {String} content
         * @returns {String}
         */
        _highlightBasedOnThreadSearch(content) {
            if (this.threads) {
                for (const thread of this.threads) {
                    if (thread.searchedText) {
                        // this regex ignores html tags
                        const pattern = `(?<!<\/?[^>]*|&[^;]*)(${escapeRegExp(thread.searchedText)})`
                        content = content.replace(
                            new RegExp(pattern,"ig"),
                            '<b class="o_MessageInlineHighlight">$1</b>'
                        );
                    }
                }
            }
            return content;
        }

        /**
         * Adds Read More and Read Less togglers for the collapsable contents.
         * 
         * @param {String} content String rep of the DOM Content
         * @param {Boolean} shouldOpenChidlrenRecursively 
         * When opening a collapsable content, should it open all the children as well ?
         * Making the effective depth of the collapsable equals 1.
         * @returns String rep of the DOM Content processed
         */
        _insertMoreOrLessTogglersForCollapsableContent(content, shouldOpenChidlrenRecursively = false) {
            /**
             * For simplicity, we need to manipulate a DOM Element directly.
             * Note that "unvalid" html, like nested <p> will get unested by this procedure.
             * So the better the html conventions are respected, the better this will work.
             */
            const contentAsHMTL = document.createElement('div');
            contentAsHMTL.innerHTML = content;

            /**
             * For any element with id "stopSpelling", all the following text nodes siblings
             * nedd to get collapsed. So we add to them the data-o-mail-quote that will 
             * trigger later the callapsable behavior.
             */
            let stopSpellings = contentAsHMTL.querySelectorAll("#stopSpelling");
            for (const stopSpelling of stopSpellings) {
                let current = stopSpelling.nextSibling
                while (current) {
                    const next = current.nextSibling
                    if (current.nodeType === 3 && current.textContent.trim()) { 
                        var spanNode = document.createElement('span');
                        spanNode.dataset.oMailQuote = true;
                        var newTextNode = document.createTextNode(current.textContent);
                        spanNode.appendChild(newTextNode);
                        current.parentNode.replaceChild(spanNode, current);
                    }
                    current = next;
                }
            }

            /**
             * While there is a collapsable element in the dom, we need to process it. 
             * We remove the data-o-mail-quote attr when the processing is done.
             */
            let collapsable = contentAsHMTL.querySelector("[data-o-mail-quote]");
            while (collapsable) {
                collapsable.removeAttribute("data-o-mail-quote");
                /**
                 * We create a hash based on the content of the node. 
                 * We need to do this because we have no other way to compare nodes at each different update.
                 * We use the message id as prefix to make sure not to modify other messages that could have the same content.
                 * It will be kept in a map to keep track of the opened/closed state of the collapsable contents.
                 */
                const hash = this.id + '_' + collapsable.innerHTML.split('').reduce((a, b) => { a = ((a << 5) - a) + b.charCodeAt(0); return a & a }, 0);
                /**
                 * If the map keeping track of the opened collapsable contents contains the current hash, it means it's opened. 
                 * So we keep the content and add a Read Less possibility.
                 * Otherwise, we replace the content by Read Less possibility.
                 */
                if(this.currentlyOpenedReadMoreHashes.has(hash)) {
                    /** 
                     * If the children must all be open recursively, we simply remove all the data-o-mail-quote attributes on
                     * the chidlren elements.
                     */
                    if (shouldOpenChidlrenRecursively) {
                        const elements = collapsable.querySelectorAll("[data-o-mail-quote]");
                        for (const element of elements) {
                            element.removeAttribute("data-o-mail-quote");
                        }
                    }
                    collapsable.outerHTML = `<span class="o_Message_readMoreLess" data-read-less-hash="${hash}">${READ_LESS}</span>` + collapsable.outerHTML;
                }
                else {
                    collapsable.outerHTML = `<span class="o_Message_readMoreLess" data-read-more-hash="${hash}">${READ_MORE}</span>`
                } 
                collapsable = contentAsHMTL.querySelector("[data-o-mail-quote]");
            }
            /**
             * We used a DOM Element, but all the process use DOM as string, so we get
             * back the inner html.
             */
            return contentAsHMTL.innerHTML;
        }

        /**
         * Determines if the message is in a search context,
         * in other words, if the user is searching through the messages with the search box
         * 
         * @private
         * @returns {Boolean}
         */
        _isThreadCurrentlyBeingSearched() {
            return this.threads.some(
                (thread) => thread.threadViews.some(
                    (threadView) => threadView.threadViewer.hasVisibleSearchBox
                )
            )
        }

        /**
         * Wraps emojis with a span to give them a class for formatting. 
         * 
         * @private
         * @param {String} content
         * @returns {String}
         */
        _wrapEmojisForFormatting(content) {
            let processedContent;
            for (const emoji of emojis) {
                const { unicode } = emoji;
                const regexp = new RegExp(
                    `(?:^|\\s|<[a-z]*>)(${unicode})(?=\\s|$|</[a-z]*>)`,
                    "g"
                );
                processedContent = content.replace(
                    regexp,
                    ` <span class="o_mail_emoji">${unicode}</span> `
                );
                // Idiot-proof limit. If the user had the amazing idea of
                // copy-pasting thousands of emojis, the image rendering can lead
                // to memory overflow errors on some browsers (e.g. Chrome). Set an
                // arbitrary limit to 200 from which we simply don't replace them
                // (anyway, they are already replaced by the unicode counterpart).
                if (_.str.count(processedContent, "o_mail_emoji") > 200) {
                    processedContent = content;
                }
            }
            return processedContent;
        }

    }

    Message.fields = {
        actionList: one2one('mail.message_action_list', {
            default: create(),
            inverse: 'message',
            isCausal: true,
            readonly: true,
        }),
        currentlyOpenedReadMoreHashes: attr({
            default: new Set(),
        }),
        attachments: many2many('mail.attachment', {
            inverse: 'messages',
        }),
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one2one('mail.attachment_list', {
            default: create(),
            inverse: 'message',
            isCausal: true,
            readonly: true,
            required: true,
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
        * The composer in editing mode of a message.
        */
        composerInEditing: one2one('mail.composer', {
            inverse: 'messageInEditing',
            isCausal: true,
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
        }),
        email_from: attr(),
        failureNotifications: one2many('mail.notification', {
            compute: '_computeFailureNotifications',
        }),
        guestAuthor: many2one('mail.guest', {
            inverse: 'authoredMessages',
        }),
        id: attr({
            required: true,
        }),
        isCurrentUserOrGuestAuthor: attr({
            compute: '_computeIsCurrentUserOrGuestAuthor',
            default: false,
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
        /*
         * Determines whether the current user is currently editing this message.
         */
        isEditing: attr({
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
        /**
         * Groups of reactions per content allowing to know the number of
         * reactions for each.
         */
        messageReactionGroups: one2many('mail.message_reaction_group', {
            inverse: 'message',
            isCausal: true,
        }),
        message_type: attr(),
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
         * Value gone through processing to be displayed.
         * Has been escaped in the frontend. Will be used in a t-raw.
         * Based on the author.nameOrDisplayName nested field.
         */
        prettyAuthor: attr({
            compute: '_computePrettyAuthor',
        }),
        /**
         * Value gone through processing to be displayed.
         * Has already been escaped in the backend. Will be used in a t-raw.
         * Based on the body field.
         */
        prettyBody: attr({
            compute: '_computePrettyBody',
        }),
        /**
         * Value gone through processing to be displayed.
         * Has been escaped in the frontend. Will be used in a t-raw.
         * Based on the subject field.
         */
        prettySubject: attr({
            compute: '_computePrettySubject',
        }),
       /**
         * Value gone through processing to be displayed.
         * Has been escaped in the frontend. Will be used in a t-raw.
         * Based on the subtypeDescription field.
         */
        prettySubtypeDescription: attr({
            compute: '_computePrettySubtypeDescription',
        }),
       /**
         * Value gone through processing to be displayed.
         * Has been escaped in the frontend. Will be used in a t-raw.
         * Based on the getter "trackingValues".
         */
        prettyTrackingValues: attr({
            compute: '_computePrettyTrackingValues',
        }),
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

    Message.modelName = 'mail.message';

    return Message;
}

registerNewModel('mail.message', factory);
