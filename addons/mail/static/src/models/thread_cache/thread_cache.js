odoo.define('mail/static/src/models/thread_cache/thread_cache.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field.js');

const MESSAGE_FETCH_LIMIT = 30;

function factory(dependencies) {

    class ThreadCache extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Load this thread cache, by fetching the most recent messages in this
         * conversation.
         */
        async loadMessages() {
            if (this.isLoaded && this.isLoading) {
                return;
            }
            const searchDomain = JSON.parse(this.stringifiedDomain);
            let domain = searchDomain.length ? searchDomain : [];
            domain = this._extendMessageDomain(domain);
            this.update({ isLoading: true });
            let messagesData = [];
            if (!this.thread.isTemporary) {
                messagesData = await this.async(() => this.env.services.rpc({
                    model: 'mail.message',
                    method: 'message_fetch',
                    args: [domain],
                    kwargs: this._getFetchMessagesKwargs(),
                }, { shadow: true }));
            }
            this._handleMessagesLoaded(messagesData);
        }

        async loadMoreMessages() {
            const searchDomain = JSON.parse(this.stringifiedDomain);
            let domain = searchDomain.length ? searchDomain : [];
            domain = this._extendMessageDomain(domain);
            if (this.isAllHistoryLoaded && this.isLoadingMore) {
                return;
            }
            this.update({ isLoadingMore: true });
            const minMessageId = Math.min(
                ...this.fetchedMessages.map(message => message.id)
            );
            domain = [['id', '<', minMessageId]].concat(domain);
            const messagesData = await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: this._getFetchMessagesKwargs(),
            }, { shadow: true }));
            for (const viewer of this.thread.viewers) {
                viewer.addComponentHint('more-messages-loaded');
            }
            this._handleMessagesLoaded(messagesData);
        }

        async loadNewMessages() {
            if (this.isLoading) {
                return;
            }
            if (!this.isLoaded) {
                await this.async(() => this.loadMessages());
                return;
            }
            const messageIds = this.fetchedMessages.map(message => message.id);
            const searchDomain = JSON.parse(this.stringifiedDomain);
            let domain = searchDomain.length ? searchDomain : [];
            domain = this._extendMessageDomain(domain);
            if (messageIds.length > 0) {
                const lastMessageId = Math.max(...messageIds);
                domain = [['id', '>', lastMessageId]].concat(domain);
            }
            this.update({ isLoading: true });
            const messageFetchKwargs = this._getFetchMessagesKwargs();
            messageFetchKwargs.limit = false;
            const messagesData = await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: messageFetchKwargs,
            }, { shadow: true }));
            this._handleMessagesLoaded(messagesData);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeFetchedMessages() {
            if (!this.thread) {
                return [['unlink-all']];
            }
            const toUnlinkMessages = [];
            for (const message of this.fetchedMessages) {
                if (!this.thread.messages.includes(message)) {
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
            } = this.orderedFetchedMessages;
            if (!lastFetchedMessage) {
                return [['unlink-all']];
            }
            return [['replace', lastFetchedMessage]];
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedMessages;
            if (!lastMessage) {
                return [['unlink-all']];
            }
            return [['replace', lastMessage]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeMessages() {
            if (!this.thread) {
                return [['unlink-all']];
            }
            let messages = this.fetchedMessages;
            if (this.stringifiedDomain !== '[]') {
                // AKU TODO: flag for invalidation if there are newer messages
                // in thread. task-2171873
                return [['replace', messages]];
            }
            // main cache: adjust with newer messages
            let newerMessages;
            if (!this.lastFetchedMessage) {
                newerMessages = this.thread.messages;
            } else {
                newerMessages = this.thread.messages.filter(message =>
                    message.id > this.lastFetchedMessage.id
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
            return [['replace', this.fetchedMessages.sort((m1, m2) => m1.id < m2.id ? -1 : 1)]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return [['replace', this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1)]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeUncheckedMessages() {
            return [['replace', this.messages.filter(
                message => message.hasCheckbox && !this.checkedMessages.includes(message)
            )]];
        }

        /**
         * @override
         */
        _createRecordLocalId(data) {
            const {
                stringifiedDomain = '[]',
                thread: [[commandInsert, thread]],
            } = data;
            const ThreadCache = this.env.models['mail.thread_cache'];
            return `${ThreadCache.modelName}_[${thread.localId}]_<${stringifiedDomain}>`;
        }

        /**
         * @private
         * @param {Array} domain
         * @returns {Array}
         */
        _extendMessageDomain(domain) {
            const thread = this.thread;
            if (thread.model === 'mail.channel') {
                return domain.concat([['channel_ids', 'in', [thread.id]]]);
            } else if (thread === this.env.messaging.inbox) {
                return domain.concat([['needaction', '=', true]]);
            } else if (thread === this.env.messaging.starred) {
                return domain.concat([['starred', '=', true]]);
            } else if (thread === this.env.messaging.history) {
                return domain.concat([['needaction', '=', false]]);
            } else if (thread === this.env.messaging.moderation) {
                return domain.concat([['need_moderation', '=', true]]);
            } else {
                return domain.concat([['model', '=', thread.model], ['res_id', '=', thread.id]]);
            }
        }

        /**
         * @private
         * @returns {Object}
         */
        _getFetchMessagesKwargs() {
            const thread = this.thread;
            let kwargs = {
                limit: MESSAGE_FETCH_LIMIT,
                context: this.env.session.user_context,
            };
            if (thread.moderation) {
                // thread is a channel
                kwargs.moderated_channel_ids = [thread.id];
            }
            return kwargs;
        }

        /**
         * @private
         * @param {Object[]} messageData
         */
        _handleMessagesLoaded(messagesData) {
            const messages = messagesData.map(data =>
                this.env.models['mail.message'].insert(
                    this.env.models['mail.message'].convertData(data)
                )
            );

            if (!this.thread) {
                return;
            }
            this.thread.update({
                messageSeenIndicators: [[
                    'insert',
                    messagesData.map(messageData => {
                        return {
                            id: this.env.models['mail.message_seen_indicator'].computeId(messageData.id, this.thread.id),
                            message: [['insert', { id: messageData.id }]],
                        };
                    })
                ]],
            });
            this.update({
                fetchedMessages: [['link', messages]],
                isAllHistoryLoaded: messagesData.length < MESSAGE_FETCH_LIMIT,
                isLoaded: true,
                isLoading: false,
                isLoadingMore: false,
            });
            for (const viewer of this.thread.viewers) {
                viewer.handleThreadCacheLoaded(this);
            }
        }

    }

    ThreadCache.fields = {
        checkedMessages: many2many('mail.message', {
            inverse: 'checkedThreadCaches',
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
        fetchedMessages: many2many('mail.message', {
            // adjust with messages unlinked from thread
            compute: '_computeFetchedMessages',
            dependencies: ['threadMessages'],
        }),
        isAllHistoryLoaded: attr({
            default: false,
        }),
        isLoaded: attr({
            default: false,
        }),
        isLoading: attr({
            default: false,
        }),
        isLoadingMore: attr({
            default: false,
        }),
        /**
         * Last message that has been fetched by this thread cache.
         *
         * This DOES NOT necessarily mean the last message linked to this thread
         * cache (@see lastMessage field for that). @see fetchedMessages field
         * for a deeper explanation about "fetched" messages.
         */
        lastFetchedMessage: many2one('mail.message', {
            compute: '_computeLastFetchedMessage',
            dependencies: ['orderedFetchedMessages'],
        }),
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: ['orderedMessages'],
        }),
        messagesCheckboxes: attr({
            related: 'messages.hasCheckbox',
        }),
        /**
         * List of messages linked to this cache.
         */
        messages: many2many('mail.message', {
            compute: '_computeMessages',
            dependencies: [
                'fetchedMessages',
                'threadMessages',
            ],
        }),
        /**
         * Ordered list of messages that have been fetched by this cache.
         *
         * This DOES NOT necessarily includes all messages linked to this thread
         * cache (@see orderedMessages field for that). @see fetchedMessages
         * field for deeper explanation about "fetched" messages.
         */
        orderedFetchedMessages: many2many('mail.message', {
            compute: '_computeOrderedFetchedMessages',
            dependencies: ['fetchedMessages'],
        }),
        /**
         * Ordered list of messages linked to this cache.
         */
        orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
            dependencies: ['messages'],
        }),
        stringifiedDomain: attr({
            default: '[]',
        }),
        thread: many2one('mail.thread', {
            inverse: 'caches',
        }),
        threadMessages: many2many('mail.message', {
            related: 'thread.messages',
        }),
        uncheckedMessages: many2many('mail.message', {
            compute: '_computeUncheckedMessages',
            dependencies: [
                'checkedMessages',
                'messagesCheckboxes',
                'messages',
            ],
        }),
    };

    ThreadCache.modelName = 'mail.thread_cache';

    return ThreadCache;
}

registerNewModel('mail.thread_cache', factory);

});
