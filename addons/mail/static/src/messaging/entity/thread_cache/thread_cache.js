odoo.define('mail.messaging.entity.ThreadCache', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

const MESSAGE_FETCH_LIMIT = 30;

function ThreadCacheFactory({ Entity }) {

    class ThreadCache extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {mail.messaging.entity.Message|undefined}
         */
        get lastMessage() {
            const { length: l, [l - 1]: lastMessage } = this.orderedMessages;
            return lastMessage;
        }

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
                messagesData = await this.env.rpc({
                    model: 'mail.message',
                    method: 'message_fetch',
                    args: [domain],
                    kwargs: this._getFetchMessagesKwargs(),
                }, { shadow: true });
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
            const messagesData = await this.env.rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: this._getFetchMessagesKwargs(),
            }, { shadow: true });
            for (const viewer of this.thread.viewers) {
                viewer.addComponentHint('more-messages-loaded');
            }
            this._handleMessagesLoaded(messagesData);
        }

        async loadNewMessages() {
            const messageIds = this.messages.map(message => message.id);
            const searchDomain = JSON.parse(this.stringifiedDomain);
            let domain = searchDomain.length ? searchDomain : [];
            domain = this._extendMessageDomain(domain);
            if (messageIds.length > 0) {
                const lastMessageId = Math.max(...messageIds);
                domain = [['id', '>', lastMessageId]].concat(domain);
            }
            this.update({ isLoadingMore: true });
            const messageFetchKwargs = this._getFetchMessagesKwargs();
            messageFetchKwargs.limit = false;
            const messagesData = await this.env.rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: messageFetchKwargs,
            }, { shadow: true });
            this._handleMessagesLoaded(messagesData);
        }

        /**
         * @returns {mail.messaging.entity.Message[]}
         */
        get orderedMessages() {
            return this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1);
        }

        /**
         * @returns {mail.messaging.entity.Message[]}
         */
        get uncheckedMessages() {
            return this.messages.filter(
                message => message.hasCheckbox && !this.checkedMessages.includes(message)
            );
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _createInstanceLocalId(data) {
            const {
                stringifiedDomain = '[]',
                thread: threadOrLocalId,
            } = data;
            const thread = this.env.entities.Thread.get(threadOrLocalId);
            return `${this.constructor.localId}_[${thread.localId}]_<${stringifiedDomain}>`;
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
            } else if (thread.model === 'mail.box' && thread.id === 'inbox') {
                return domain.concat([['needaction', '=', true]]);
            } else if (thread.model === 'mail.box' && thread.id === 'starred') {
                return domain.concat([['starred', '=', true]]);
            } else if (thread.model === 'mail.box' && thread.id === 'history') {
                return domain.concat([['needaction', '=', false]]);
            } else if (thread.model === 'mail.box' && thread.id === 'moderation') {
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
            });
            for (const data of messagesData) {
                let message = this.env.entities.Message.insert(data);
                this.link({ messages: message });
            }
        }

        /**
         * @override
         */
        _update(data) {
            const {
                isAllHistoryLoaded = this.isAllHistoryLoaded || false,
                isLoaded = this.isLoaded || false,
                isLoading = this.isLoading || false,
                isLoadingMore = this.isLoadingMore || false,
                stringifiedDomain = this.stringifiedDomain || '[]',
                thread: threadOrLocalId,
            } = data;

            this._write({
                isAllHistoryLoaded,
                isLoaded,
                isLoading,
                isLoadingMore,
                stringifiedDomain,
            });

            if (threadOrLocalId) {
                const thread = this.env.entities.Thread.get(threadOrLocalId);
                this.link({ thread });
            }
        }

    }

    Object.assign(ThreadCache, {
        relations: Object.assign({}, Entity.relations, {
            checkedMessages: {
                inverse: 'checkedThreadCaches',
                to: 'Message',
                type: 'many2many',
            },
            thread: {
                inverse: 'caches',
                to: 'Thread',
                type: 'many2one',
            },
            messages: {
                inverse: 'threadCaches',
                to: 'Message',
                type: 'many2many',
            },
        }),
    });

    return ThreadCache;
}

registerNewEntity('ThreadCache', ThreadCacheFactory);

});
