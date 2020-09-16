odoo.define('mail/static/src/models/thread_cache/thread_cache.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ThreadCache extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {mail.message[]|undefined}
         */
        async loadMoreMessages() {
            if (
                this.__mfield_isAllHistoryLoaded(this) ||
                this.__mfield_isLoading(this)
            ) {
                return;
            }
            if (!this.__mfield_isLoaded(this)) {
                this.update({
                    __mfield_hasToLoadMessages: true,
                });
                return;
            }
            this.update({
                __mfield_isLoadingMore: true,
            });
            const messageIds = this.__mfield_fetchedMessages(this).map(message => message.__mfield_id(this));
            const limit = 30;
            const fetchedMessages = await this.async(() => this._loadMessages({
                extraDomain: [['id', '<', Math.min(...messageIds)]],
                limit,
            }));
            for (const threadView of this.__mfield_threadViews(this)) {
                threadView.addComponentHint('more-messages-loaded');
            }
            this.update({
                __mfield_isLoadingMore: false,
            });
            if (fetchedMessages.length < limit) {
                this.update({
                    __mfield_isAllHistoryLoaded: true,
                });
            }
            return fetchedMessages;
        }

        /**
         * @returns {mail.message[]|undefined}
         */
        async loadNewMessages() {
            if (this.__mfield_isLoading(this)) {
                return;
            }
            if (!this.__mfield_isLoaded(this)) {
                this.update({
                    __mfield_hasToLoadMessages: true,
                });
                return;
            }
            const messageIds = this.__mfield_fetchedMessages(this).map(message => message.__mfield_id(this));
            return this._loadMessages({
                extraDomain: [['id', '>', Math.max(...messageIds)]],
                limit: false,
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const {
                __mfield_stringifiedDomain = '[]',
                __mfield_thread: [[commandInsert, thread]],
            } = data;
            return `${this.modelName}_[${thread.localId}]_<${__mfield_stringifiedDomain}>`;
        }

        /**
         * @private
         */
        _computeCheckedMessages() {
            const messagesWithoutCheckbox = this.__mfield_checkedMessages(this).filter(
                message => !message.__mfield_hasCheckbox(this)
            );
            return [['unlink', messagesWithoutCheckbox]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeFetchedMessages() {
            if (!this.__mfield_thread(this)) {
                return [['unlink-all']];
            }
            const toUnlinkMessages = [];
            for (const message of this.__mfield_fetchedMessages(this)) {
                if (!this.__mfield_thread(this).__mfield_messages(this).includes(message)) {
                    toUnlinkMessages.push(message);
                }
            }
            return [['unlink', toUnlinkMessages]];
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastFetchedMessage() {
            const {
                length: l,
                [l - 1]: lastFetchedMessage,
            } = this.__mfield_orderedFetchedMessages(this);
            if (!lastFetchedMessage) {
                return [['unlink']];
            }
            return [['link', lastFetchedMessage]];
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.__mfield_orderedMessages(this);
            if (!lastMessage) {
                return [['unlink']];
            }
            return [['link', lastMessage]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeMessages() {
            if (!this.__mfield_thread(this)) {
                return [['unlink-all']];
            }
            let messages = this.__mfield_fetchedMessages(this);
            if (this.__mfield_stringifiedDomain(this) !== '[]') {
                // AKU TODO: flag for invalidation if there are newer messages
                // in thread. task-2171873
                return [['replace', messages]];
            }
            // main cache: adjust with newer messages
            let newerMessages;
            if (!this.__mfield_lastFetchedMessage(this)) {
                newerMessages = this.__mfield_thread(this).__mfield_messages(this);
            } else {
                newerMessages = this.__mfield_thread(this).__mfield_messages(this).filter(message =>
                    message.__mfield_id(this) > this.__mfield_lastFetchedMessage(this).__mfield_id(this)
                );
            }
            messages = messages.concat(newerMessages);
            return [['replace', messages]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedFetchedMessages() {
            return [['replace', this.__mfield_fetchedMessages(this).sort((m1, m2) =>
                m1.__mfield_id(this) < m2.__mfield_id(this) ? -1 : 1
            )]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return [['replace', this.__mfield_messages(this).sort(
                (m1, m2) => m1.__mfield_id(this) < m2.__mfield_id(this) ? -1 : 1
            )]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasToLoadMessages() {
            return (
                this.__mfield_thread(this) &&
                !this.__mfield_thread(this).__mfield_isTemporary(this) &&
                this.__mfield_threadViews(this).length > 0 &&
                !this.__mfield_isLoaded(this) &&
                !this.__mfield_isLoading(this)
            );
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeUncheckedMessages() {
            return [['replace', this.__mfield_messages(this).filter(
                message => message.__mfield_hasCheckbox(this) &&
                !this.__mfield_checkedMessages(this).includes(message)
            )]];
        }

        /**
         * @private
         * @param {Array} domain
         * @returns {Array}
         */
        _extendMessageDomain(domain) {
            const thread = this.__mfield_thread(this);
            if (thread.__mfield_model(this) === 'mail.channel') {
                return domain.concat([['channel_ids', 'in', [thread.__mfield_id(this)]]]);
            } else if (thread === this.env.messaging.__mfield_inbox(this)) {
                return domain.concat([['needaction', '=', true]]);
            } else if (thread === this.env.messaging.__mfield_starred(this)) {
                return domain.concat([
                    ['starred_partner_ids', 'in', [this.env.messaging.__mfield_currentPartner(this).__mfield_id(this)]],
                ]);
            } else if (thread === this.env.messaging.__mfield_history(this)) {
                return domain.concat([['needaction', '=', false]]);
            } else if (thread === this.env.messaging.__mfield_moderation(this)) {
                return domain.concat([['moderation_status', '=', 'pending_moderation']]);
            } else {
                // Avoid to load user_notification as these messages are not
                // meant to be shown on chatters.
                return domain.concat([
                    ['message_type', '!=', 'user_notification'],
                    ['model', '=', thread.__mfield_model(this)],
                    ['res_id', '=', thread.__mfield_id(this)],
                ]);
            }
        }

        /**
         * @private
         * @param {Object} [param0={}]
         * @param {Array[]} [param0.extraDomain]
         * @param {integer} [param0.limit=30]
         * @returns {mail.message[]}
         */
        async _loadMessages({ extraDomain, limit = 30 } = {}) {
            this.update({
                __mfield_isLoading: true,
            });
            const searchDomain = JSON.parse(this.__mfield_stringifiedDomain(this));
            let domain = searchDomain.length ? searchDomain : [];
            domain = this._extendMessageDomain(domain);
            if (extraDomain) {
                domain = extraDomain.concat(domain);
            }
            const context = this.env.session.user_context;
            const moderated_channel_ids = this.__mfield_thread(this).__mfield_moderation(this)
                ? [this.__mfield_thread(this).__mfield_id(this)]
                : undefined;
            const messages = await this.async(() =>
                this.env.models['mail.message'].performRpcMessageFetch(
                    domain,
                    limit,
                    moderated_channel_ids,
                    context,
                )
            );
            this.update({
                __mfield_fetchedMessages: [['link', messages]],
                __mfield_isLoaded: true,
                __mfield_isLoading: false,
            });
            if (!extraDomain && messages.length < limit) {
                this.update({
                    __mfield_isAllHistoryLoaded: true,
                });
            }
            return messages;
        }

        /**
         * Loads this thread cache, by fetching the most recent messages in this
         * conversation.
         *
         * @private
         */
        _onHasToLoadMessagesChanged() {
            if (!this.__mfield_hasToLoadMessages(this)) {
                return;
            }
            this._loadMessages();
        }

    }

    ThreadCache.fields = {
        __mfield_checkedMessages: many2many('mail.message', {
            compute: '_computeCheckedMessages',
            dependencies: [
                '__mfield_checkedMessages',
                '__mfield_messagesCheckboxes',
            ],
            inverse: '__mfield_checkedThreadCaches',
        }),
        /**
         * List of messages that have been fetched by this cache.
         *
         * This DOES NOT necessarily includes all messages linked to this thread
         * cache (@see messages field for that): it just contains list
         * of successive messages that have been explicitly fetched by this
         * cache. For all non-main caches, this corresponds to all messages.
         * For the main cache, however, messages received from longpolling
         * should be displayed on main cache but they have not been explicitly
         * fetched by cache, so they ARE NOT in this list (at least, not until a
         * fetch on this thread cache contains this message).
         *
         * The distinction between messages and fetched messages is important
         * to manage "holes" in message list, while still allowing to display
         * new messages on main cache of thread in real-time.
         */
        __mfield_fetchedMessages: many2many('mail.message', {
            // adjust with messages unlinked from thread
            compute: '_computeFetchedMessages',
            dependencies: [
                '__mfield_threadMessages',
            ],
        }),
        /**
         * Determines whether `this` should load initial messages.
         */
        __mfield_hasToLoadMessages: attr({
            compute: '_computeHasToLoadMessages',
            dependencies: [
                '__mfield_isLoaded',
                '__mfield_isLoading',
                '__mfield_thread',
                '__mfield_threadIsTemporary',
                '__mfield_threadViews',
            ],
        }),
        __mfield_isAllHistoryLoaded: attr({
            default: false,
        }),
        __mfield_isLoaded: attr({
            default: false,
        }),
        __mfield_isLoading: attr({
            default: false,
        }),
        __mfield_isLoadingMore: attr({
            default: false,
        }),
        /**
         * Last message that has been fetched by this thread cache.
         *
         * This DOES NOT necessarily mean the last message linked to this thread
         * cache (@see lastMessage field for that). @see fetchedMessages field
         * for a deeper explanation about "fetched" messages.
         */
        __mfield_lastFetchedMessage: many2one('mail.message', {
            compute: '_computeLastFetchedMessage',
            dependencies: [
                '__mfield_orderedFetchedMessages',
            ],
        }),
        __mfield_lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: [
                '__mfield_orderedMessages',
            ],
        }),
        __mfield_messagesCheckboxes: attr({
            related: '__mfield_messages.__mfield_hasCheckbox',
        }),
        /**
         * List of messages linked to this cache.
         */
        __mfield_messages: many2many('mail.message', {
            compute: '_computeMessages',
            dependencies: [
                '__mfield_fetchedMessages',
                '__mfield_threadMessages',
            ],
        }),
        /**
         * Loads initial messages from `this`.
         * This is not a "real" field, its compute function is used to trigger
         * the load of messages at the right time.
         */
        __mfield_onHasToLoadMessagesChanged: attr({
            compute: '_onHasToLoadMessagesChanged',
            dependencies: [
                '__mfield_hasToLoadMessages',
            ],
        }),
        /**
         * Ordered list of messages that have been fetched by this cache.
         *
         * This DOES NOT necessarily includes all messages linked to this thread
         * cache (@see orderedMessages field for that). @see fetchedMessages
         * field for deeper explanation about "fetched" messages.
         */
        __mfield_orderedFetchedMessages: many2many('mail.message', {
            compute: '_computeOrderedFetchedMessages',
            dependencies: [
                '__mfield_fetchedMessages',
            ],
        }),
        /**
         * Ordered list of messages linked to this cache.
         */
        __mfield_orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
            dependencies: [
                '__mfield_messages',
            ],
        }),
        __mfield_stringifiedDomain: attr({
            default: '[]',
        }),
        __mfield_thread: many2one('mail.thread', {
            inverse: '__mfield_caches',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_threadIsTemporary: attr({
            related: '__mfield_thread.__mfield_isTemporary',
        }),
        __mfield_threadMessages: many2many('mail.message', {
            related: '__mfield_thread.__mfield_messages',
        }),
        /**
         * States the 'mail.thread_view' that are currently displaying `this`.
         */
        __mfield_threadViews: one2many('mail.thread_view', {
            inverse: '__mfield_threadCache',
        }),
        __mfield_uncheckedMessages: many2many('mail.message', {
            compute: '_computeUncheckedMessages',
            dependencies: [
                '__mfield_checkedMessages',
                '__mfield_messagesCheckboxes',
                '__mfield_messages',
            ],
        }),
    };

    ThreadCache.modelName = 'mail.thread_cache';

    return ThreadCache;
}

registerNewModel('mail.thread_cache', factory);

});
