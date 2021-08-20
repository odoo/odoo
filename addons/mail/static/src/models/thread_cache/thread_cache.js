/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

function factory(dependencies) {

    class ThreadCache extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
                fetchedMessages = await this._loadMessages({
                    extraDomain: [['id', '<', Math.min(...messageIds)]],
                    limit,
                });
                success = true;
            } catch (e) {
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
        }

        /**
         * @returns {mail.message[]|undefined}
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
            const fetchedMessages = this._loadMessages({
                extraDomain: [['id', '>', Math.max(...messageIds)]],
                limit: false,
            });
            if (!fetchedMessages) {
                return;
            }
            for (const threadView of this.threadViews) {
                threadView.addComponentHint('new-messages-loaded', { fetchedMessages });
            }
            return fetchedMessages;
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
                return unlinkAll();
            }
            const toUnlinkMessages = [];
            for (const message of this.fetchedMessages) {
                if (!this.thread.messages.includes(message)) {
                    toUnlinkMessages.push(message);
                }
            }
            return unlink(toUnlinkMessages);
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
                return unlink();
            }
            return link(lastFetchedMessage);
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
                return unlink();
            }
            return link(lastMessage);
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeMessages() {
            if (!this.thread) {
                return unlinkAll();
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
        }

        /**
         *
         * @private
         * @returns {mail.message[]}
         */
        _computeNonEmptyMessages() {
            return replace(this.messages.filter(message => !message.isEmpty));
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedFetchedMessages() {
            return replace(this.fetchedMessages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return replace(this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        }

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
        }

        /**
         * @private
         * @param {Array} domain
         * @returns {Array}
         */
        _extendMessageDomain(domain) {
            const thread = this.thread;
            if (thread === this.messaging.inbox) {
                return domain.concat([['needaction', '=', true]]);
            } else if (thread === this.messaging.starred) {
                return domain.concat([
                    ['starred_partner_ids', 'in', [this.messaging.currentPartner.id]],
                ]);
            } else if (thread === this.messaging.history) {
                return domain.concat([['needaction', '=', false]]);
            } else {
                // Avoid to load user_notification as these messages are not
                // meant to be shown on chatters.
                return domain.concat([
                    ['message_type', '!=', 'user_notification'],
                    ['model', '=', thread.model],
                    ['res_id', '=', thread.id],
                ]);
            }
        }

        /**
         * @private
         * @param {Object} [param0={}]
         * @param {Array[]} [param0.extraDomain]
         * @param {integer} [param0.limit=30]
         * @returns {mail.message[]}
         * @throws {Error} when failed to load messages
         */
        async _loadMessages({ extraDomain, limit = 30 } = {}) {
            this.update({ isLoading: true });
            let domain = [];
            domain = this._extendMessageDomain(domain);
            if (extraDomain) {
                domain = extraDomain.concat(domain);
            }
            let messages;
            try {
                messages = await this.messaging.models['mail.message'].performRpcMessageFetch(
                    domain,
                    limit,
                );
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
            if (!extraDomain && messages.length < limit) {
                this.update({ isAllHistoryLoaded: true });
            }
            this.messaging.messagingBus.trigger('o-thread-cache-loaded-messages', {
                fetchedMessages: messages,
                threadCache: this,
            });
            return messages;
        }

        /**
         * Split method for `_computeHasToLoadMessages` because it has to write
         * on 2 fields at once which is not supported by standard compute.
         *
         * @private
         */
        _onChangeForHasToLoadMessages() {
            this.update(this._computeHasToLoadMessages());
        }

        /**
         * Calls "mark all as read" when this thread becomes displayed in a
         * view (which is notified by `isMarkAllAsReadRequested` being `true`),
         * but delays the call until some other conditions are met, such as the
         * messages being loaded.
         * The reason to wait until messages are loaded is to avoid a race
         * condition because "mark all as read" will change the state of the
         * messages in parallel to fetch reading them.
         *
         * @private
         */
        _onChangeMarkAllAsRead() {
            if (
                !this.isMarkAllAsReadRequested ||
                !this.isLoaded ||
                this.isLoading
            ) {
                // wait for change of state before deciding what to do
                return;
            }
            this.update({ isMarkAllAsReadRequested: false });
            if (
                this.thread.isTemporary ||
                this.thread.model === 'mail.box' ||
                this.threadViews.length === 0
            ) {
                // ignore the request
                return;
            }
            this.messaging.models['mail.message'].markAllAsRead([
                ['model', '=', this.thread.model],
                ['res_id', '=', this.thread.id],
            ]);
        }

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
            let fetchedMessages;
            try {
                fetchedMessages = await this._loadMessages();
            } catch (e) {
                return;
            }
            for (const threadView of this.threadViews) {
                threadView.addComponentHint('messages-loaded', { fetchedMessages });
            }
        }

    }

    ThreadCache.fields = {
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
         * Determines whether this cache should consider calling "mark all as
         * read" on this thread.
         *
         * This field is a hint that may or may not lead to an actual call.
         * @see `_onChangeMarkAllAsRead`
         */
        isMarkAllAsReadRequested: attr({
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
        }),
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
        }),
        /**
         * List of messages linked to this cache.
         */
        messages: many2many('mail.message', {
            compute: '_computeMessages',
        }),
        /**
         * List of non empty messages linked to this cache.
         */
        nonEmptyMessages: many2many('mail.message', {
            compute: '_computeNonEmptyMessages',
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
        }),
        /**
         * Ordered list of messages linked to this cache.
         */
        orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
        }),
        thread: one2one('mail.thread', {
            inverse: 'cache',
        }),
        /**
         * States the 'mail.thread_view' that are currently displaying `this`.
         */
        threadViews: one2many('mail.thread_view', {
            inverse: 'threadCache',
        }),
    };
    ThreadCache.onChanges = [
        new OnChange({
            dependencies: ['hasLoadingFailed', 'isCacheRefreshRequested', 'isLoaded', 'isLoading', 'thread.isTemporary', 'threadViews'],
            methodName: '_onChangeForHasToLoadMessages',
        }),
        new OnChange({
            dependencies: ['isLoaded', 'isLoading', 'isMarkAllAsReadRequested', 'thread.isTemporary', 'thread.model', 'threadViews'],
            methodName: '_onChangeMarkAllAsRead',
        }),
        new OnChange({
            dependencies: ['hasToLoadMessages'],
            methodName: '_onHasToLoadMessagesChanged',
        }),
    ];
    ThreadCache.modelName = 'mail.thread_cache';

    return ThreadCache;
}

registerNewModel('mail.thread_cache', factory);
