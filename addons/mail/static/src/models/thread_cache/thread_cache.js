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
                ...this.messages.map(message => message.id)
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
            const messageIds = this.messages.map(message => message.id);
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
         * @returns {mail.message|undefined}
         */
        _computeLastMessage() {
            const { length: l, [l - 1]: lastMessage } = this.orderedMessages;
            if (!lastMessage) {
                return [['unlink-all']];
            }
            return [['replace', lastMessage]];
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
            this.update({
                isAllHistoryLoaded: messagesData.length < MESSAGE_FETCH_LIMIT,
                isLoaded: true,
                isLoading: false,
                isLoadingMore: false,
                messages: [['insert', messagesData.map(data =>
                    this.env.models['mail.message'].convertData(data))
                ]],
            });
            if (!this.thread) {
                return;
            }
            this.thread.update({
                messageSeenIndicators: [['insert', messagesData.map(messageData => {
                    return {
                        id: this.env.models['mail.message_seen_indicator'].computeId(messageData.id, this.thread.id),
                        message: [['insert', { id: messageData.id }]],
                    };
                })]],
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
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: ['orderedMessages'],
        }),
        messagesCheckboxes: attr({
            related: 'messages.hasCheckbox',
        }),
        messages: many2many('mail.message', {
            inverse: 'threadCaches',
        }),
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
