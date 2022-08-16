/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, link, replace, unlink } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'ThreadCache',
    recordMethods: {
        async loadMoreMessages() {
            if (this.isAllHistoryLoaded || this.isLoading) {
                return;
            }
            if (!this.isLoaded) {
                this.update({ isCacheRefreshRequested: true });
                return;
            }
            this.update({ isLoadingMore: true });
            const messageIds = this.fetchedMessages.map(message => message.id);
            const limit = 30;
            let fetchedMessages;
            let success;
            try {
                fetchedMessages = await this._loadMessages({ limit, maxId: Math.min(...messageIds) });
                success = true;
            } catch (_e) {
                success = false;
            }
            if (!this.exists()) {
                return;
            }
            if (success) {
                if (fetchedMessages.length < limit) {
                    this.update({ isAllHistoryLoaded: true });
                }
                for (const threadView of this.threadViews) {
                    threadView.addComponentHint('more-messages-loaded', { fetchedMessages });
                }
            }
            this.update({ isLoadingMore: false });
        },
        /**
         * @returns {Message[]|undefined}
         */
        async loadNewMessages() {
            if (this.isLoading) {
                return;
            }
            if (!this.isLoaded) {
                this.update({ isCacheRefreshRequested: true });
                return;
            }
            const messageIds = this.fetchedMessages.map(message => message.id);
            const fetchedMessages = this._loadMessages({ minId: Math.max(...messageIds, 0) });
            if (!fetchedMessages || fetchedMessages.length === 0) {
                return;
            }
            for (const threadView of this.threadViews) {
                threadView.addComponentHint('new-messages-loaded', { fetchedMessages });
            }
            return fetchedMessages;
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeFetchedMessages() {
            if (!this.thread) {
                return clear();
            }
            const toUnlinkMessages = [];
            for (const message of this.fetchedMessages) {
                if (!this.thread.messages.includes(message)) {
                    toUnlinkMessages.push(message);
                }
            }
            return unlink(toUnlinkMessages);
        },
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeLastFetchedMessage() {
            const {
                length: l,
                [l - 1]: lastFetchedMessage,
            } = this.orderedFetchedMessages;
            if (!lastFetchedMessage) {
                return clear();
            }
            return replace(lastFetchedMessage);
        },
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedMessages;
            if (!lastMessage) {
                return clear();
            }
            return replace(lastMessage);
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeMessages() {
            if (!this.thread) {
                return clear();
            }
            let newerMessages;
            if (!this.lastFetchedMessage) {
                newerMessages = this.thread.messages;
            } else {
                newerMessages = this.thread.messages.filter(message =>
                    message.id > this.lastFetchedMessage.id
                );
            }
            return replace(this.fetchedMessages.concat(newerMessages));
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeOrderedFetchedMessages() {
            return replace(this.fetchedMessages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeOrderedMessages() {
            return replace(this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        },
        /**
         *
         * @private
         * @returns {Message[]}
         */
        _computeOrderedNonEmptyMessages() {
            return replace(this.orderedMessages.filter(message => !message.isEmpty));
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasToLoadMessages() {
            const res = { hasToLoadMessages: false };
            if (!this.thread) {
                // happens during destroy or compute executed in wrong order
                return res;
            }
            if (this.hasLoadingFailed) {
                return res;
            }
            const wasCacheRefreshRequested = this.isCacheRefreshRequested;
            // mark hint as processed
            if (this.isCacheRefreshRequested) {
                res.isCacheRefreshRequested = false;
            }
            if (this.thread.isTemporary) {
                // temporary threads don't exist on the server
                return res;
            }
            if (!wasCacheRefreshRequested && this.threadViews.length === 0) {
                // don't load message that won't be used
                return res;
            }
            if (this.isLoading) {
                // avoid duplicate RPC
                return res;
            }
            if (!wasCacheRefreshRequested && this.isLoaded) {
                // avoid duplicate RPC
                return res;
            }
            if (this.isLoaded) {
                // Ignore request if it is already loaded or loading. Indeed
                // messages are automatically sync with server updates already,
                // so there is never a need to refresh it past the first time.
                return res;
            }
            res.hasToLoadMessages = true;
            return res;
        },
        /**
         * @private
         * @param {Object} [param0={}]
         * @param {integer} [param0.limit=30]
         * @param {integer} [param0.maxId]
         * @param {integer} [param0.minId]
         * @returns {Message[]}
         * @throws {Error} when failed to load messages
         */
        async _loadMessages({ limit = 30, maxId, minId } = {}) {
            this.update({ isLoading: true });
            let messages;
            try {
                messages = await this.messaging.models['Message'].performRpcMessageFetch(this.thread.fetchMessagesUrl, {
                    ...this.thread.fetchMessagesParams,
                    limit,
                    'max_id': maxId,
                    'min_id': minId,
                });
            } catch (e) {
                if (this.exists()) {
                    this.update({
                        hasLoadingFailed: true,
                        isLoading: false,
                    });
                }
                throw e;
            }
            if (!this.exists()) {
                return;
            }
            this.update({
                fetchedMessages: link(messages),
                hasLoadingFailed: false,
                isLoaded: true,
                isLoading: false,
            });
            if (!minId && messages.length < limit) {
                this.update({ isAllHistoryLoaded: true });
            }
            this.messaging.messagingBus.trigger('o-thread-cache-loaded-messages', {
                fetchedMessages: messages,
                threadCache: this,
            });
            return messages;
        },
        /**
         * Split method for `_computeHasToLoadMessages` because it has to write
         * on 2 fields at once which is not supported by standard compute.
         *
         * @private
         */
        _onChangeForHasToLoadMessages() {
            this.update(this._computeHasToLoadMessages());
        },
        /**
         * Loads this thread cache, by fetching the most recent messages in this
         * conversation.
         *
         * @private
         */
        async _onHasToLoadMessagesChanged() {
            if (!this.hasToLoadMessages) {
                return;
            }
            const fetchedMessages = await this._loadMessages();
            if (!this.exists()) {
                return;
            }
            for (const threadView of this.threadViews) {
                threadView.addComponentHint('messages-loaded', { fetchedMessages });
            }
            this.messaging.messagingBus.trigger('o-thread-loaded-messages', { thread: this.thread });
        },
    },
    fields: {
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
        fetchedMessages: many('Message', {
            compute: '_computeFetchedMessages',
        }),
        /**
         * Determines whether the last message fetch failed.
         */
        hasLoadingFailed: attr({
            default: false,
        }),
        /**
         * Determines whether `this` should load initial messages.
         * @see `onChangeForHasToLoadMessages` value of this field is mainly set
         *  from this "on change".
         * @see `isCacheRefreshRequested` to request manual refresh of messages.
         */
        hasToLoadMessages: attr(),
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
         * Determines whether `this` should consider refreshing its messages.
         * This field is a hint that may or may not lead to an actual refresh.
         * @see `hasToLoadMessages`
         */
        isCacheRefreshRequested: attr({
            default: false,
        }),
        /**
         * Last message that has been fetched by this thread cache.
         *
         * This DOES NOT necessarily mean the last message linked to this thread
         * cache (@see lastMessage field for that). @see fetchedMessages field
         * for a deeper explanation about "fetched" messages.
         */
        lastFetchedMessage: one('Message', {
            compute: '_computeLastFetchedMessage',
        }),
        lastMessage: one('Message', {
            compute: '_computeLastMessage',
        }),
        /**
         * List of messages linked to this cache.
         */
        messages: many('Message', {
            compute: '_computeMessages',
        }),
        /**
         * Ordered list of messages that have been fetched by this cache.
         *
         * This DOES NOT necessarily includes all messages linked to this thread
         * cache (@see orderedMessages field for that). @see fetchedMessages
         * field for deeper explanation about "fetched" messages.
         */
        orderedFetchedMessages: many('Message', {
            compute: '_computeOrderedFetchedMessages',
        }),
        /**
         * Ordered list of messages linked to this cache.
         */
        orderedMessages: many('Message', {
            compute: '_computeOrderedMessages',
        }),
        /**
         * List of ordered non empty messages linked to this cache.
         */
        orderedNonEmptyMessages: many('Message', {
            compute: '_computeOrderedNonEmptyMessages',
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'cache',
            readonly: true,
            required: true,
        }),
        /**
         * States the 'ThreadView' that are currently displaying `this`.
         */
        threadViews: many('ThreadView', {
            inverse: 'threadCache',
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['hasLoadingFailed', 'isCacheRefreshRequested', 'isLoaded', 'isLoading', 'thread.isTemporary', 'threadViews'],
            methodName: '_onChangeForHasToLoadMessages',
        }),
        new OnChange({
            dependencies: ['hasToLoadMessages'],
            methodName: '_onHasToLoadMessagesChanged',
        }),
    ],
});
