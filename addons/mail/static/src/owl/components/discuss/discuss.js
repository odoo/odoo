odoo.define('mail.component.Discuss', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const Composer = require('mail.component.Composer');
const MobileMailboxSelection = require('mail.component.DiscussMobileMailboxSelection');
const Sidebar = require('mail.component.DiscussSidebar');
const MobileNavbar = require('mail.component.MobileMessagingNavbar');
const Thread = require('mail.component.Thread');
const ThreadPreviewList = require('mail.component.ThreadPreviewList');

const { Component, useState } = owl;
const { useDispatch, useGetters, useRef, useStore } = owl.hooks;

class Discuss extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether current user is currently adding a channel from
             * the sidebar.
             */
            isAddingChannel: false,
            /**
             * Determine whether current user is currently adding a chat from
             * the sidebar.
             */
            isAddingChat: false,
            /**
             * Determine whether current user is currently replying to a message
             * from inbox.
             */
            isReplyingToMessage: false,
            /**
             * Counter used to track replying message in discuss from the store.
             */
            replyingToMessageCounter: 0,
            /**
             * If the current is currently replying to a message from inbox,
             * this is the local id of the message.
             */
            replyingToMessageMessageLocalId: undefined,
            /**
             * If the current is currently replying to a message from inbox,
             * this is the local id of the thread to reply the message to.
             */
            replyingToMessageThreadLocalId: undefined,
            threadCachesStoredScrollTop: {}, // key: threadCachelocalId, value: { value } (obj. to prevent 0 being falsy)
        });
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore(state => {
            const {
                activeThreadLocalId,
                stringifiedDomain,
            } = state.discuss;
            const activeThread = state.threads[activeThreadLocalId];
            const activeThreadCacheLocalId = activeThread
                ? activeThread.cacheLocalIds[stringifiedDomain]
                : undefined;
            const activeThreadCache = activeThreadCacheLocalId
                ? state.threadCaches[activeThreadCacheLocalId]
                : undefined;
            return Object.assign({}, state.discuss, {
                activeThread,
                activeThreadCache,
                activeThreadCacheLocalId,
                // intentionally keep unsynchronize value of old thread counter
                // useful in willUpdateProps to detect change of counter
                activeThreadCounter: activeThread && activeThread.counter,
                isMessagingReady: state.isMessagingReady,
                isMobile: state.isMobile,
            });
        });
        /**
         * Value that is used to create a channel from the sidebar.
         */
        this._addingChannelValue = "";
        /**
         * Locally tracked store props `activeThreadCacheLocalId`.
         * Useful to-set scroll position from last stored one.
         */
        this._activeThreadCacheLocalId = null;
        /**
         * Locally tracked store props `inboxMarkAsReadCounter`.
         */
        this._inboxMarkAsReadCounter = 0;
        /**
         * Reference of the composer that is used to reply to messages from
         * inbox. Useful to auto-set focus when starting reply operation.
         */
        this._replyingToMessageComposerRef = useRef('replyingToMessageComposer');
        /**
         * Reference of the thread. Useful to update scroll position correctly
         * on patch. AKU TODO: this made sense when composer was outside of
         * thread, but this may no longer be necessary??
         */
        this._threadRef = useRef('thread');
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = {};
        /**
         * Info tracked during will patch, used to determine whether the replying
         * composer should be autofocus or not. This is useful in order to auto
         * scroll to composer when it is automatically focused in mobile.
         */
        this._wp = {
            isReplyingToMessage: false,
            replyingToMessageCounter: 0,
        };
        /**
         * Determine whether messaging was ready before previous mounted/patched
         * of discuss. Useful to delay opening thread when messaging is not yet
         * ready. This is important because data on thread may require messaging
         * to be ready.
         */
        this._wasMessagingReady = false;

        // bind since passed as props
        this._onAddChannelAutocompleteSelect = this._onAddChannelAutocompleteSelect.bind(this);
        this._onAddChannelAutocompleteSource = this._onAddChannelAutocompleteSource.bind(this);
        this._onAddChatAutocompleteSelect = this._onAddChatAutocompleteSelect.bind(this);
        this._onAddChatAutocompleteSource = this._onAddChatAutocompleteSource.bind(this);
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
    }

    mounted() {
        // TODO SEB clean up this
        this.storeDispatch('updateDiscuss', {
            activeThreadLocalId: this.props.initActiveThreadLocalId,
            isOpen: true,
        });
        if (this.storeProps.activeThread) {
            this.trigger('o-push-state-action-manager', {
                activeThreadLocalId: this.props.initActiveThreadLocalId,
            });
        } else if (this.storeProps.isMessagingReady) {
            this.storeDispatch('openThread', this.props.initActiveThreadLocalId, {
                resetDiscussDomain: true,
            });
        }
        this._activeThreadCacheLocalId = this.storeProps.activeThreadCacheLocalId;
        this._wasMessagingReady = this.storeProps.isMessagingReady;
    }

    /**
     * AKU TODO: move this code to patched() hook
     */
    willUpdateProps(nextProps) {
        const activeThread = this.storeProps.activeThread;
        if (!activeThread) {
            return;
        }
        if (nextProps.activeThreadLocalId !== this.storeProps.activeThreadLocalId) {
            this.trigger('o-push-state-action-manager', {
                activeThreadLocalId: nextProps.activeThreadLocalId,
            });
        }
    }

    willPatch() {
        const shouldFocusReplyComposer =
            this.state.isReplyingToMessage &&
            (
                !this._wp.isReplyingToMessage ||
                this._wp.replyingToMessageCounter !== this.state.replyingToMessageCounter
            );
        Object.assign(this._wp, {
            isReplyingToMessage: this.state.isReplyingToMessage,
            replyingToMessageCounter: this.state.replyingToMessageCounter,
        });
        this._willPatchSnapshot = { shouldFocusReplyComposer };
    }

    patched() {
        if (this._willPatchSnapshot.shouldFocusReplyComposer) {
            // FIXME: does not work the 1st time on iOS for some reasons
            this._replyingToMessageComposerRef.comp.focus();
        }
        this.trigger('o-update-control-panel');
        this.trigger('o-push-state-action-manager', {
            activeThreadLocalId: this.storeProps.activeThreadLocalId,
        });
        if (this._inboxMarkAsReadCounter < this.storeProps.inboxMarkAsReadCounter) {
            this.trigger('o-show-rainbow-man');
        }
        if (!this._wasMessagingReady && this.storeProps.isMessagingReady) {
            this.storeDispatch('openThread', this.props.initActiveThreadLocalId, {
                resetDiscussDomain: true,
            });
        }
        this._activeThreadCacheLocalId = this.storeProps.activeThreadCacheLocalId;
        this._inboxMarkAsReadCounter = this.storeProps.inboxMarkAsReadCounter;
        this._willPatchSnapshot = {};
        this._wasMessagingReady = this.storeProps.isMessagingReady;
    }

    willUnmount() {
        this.storeDispatch('closeDiscuss');
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get addChannelInputPlaceholder() {
        return this.env._t("Create or search channel...");
    }

    /**
     * @return {string}
     */
    get addChatInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @return {Object[]}
     */
    get mobileNavbarTabs() {
        return [{
            icon: 'fa fa-inbox',
            id: 'mailbox',
            label: this.env._t("Mailboxes"),
        }, {
            icon: 'fa fa-user',
            id: 'chat',
            label: this.env._t("Chat"),
        }, {
            icon: 'fa fa-users',
            id: 'channel',
            label: this.env._t("Channel"),
        }];
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    doMobileNewChannel() {
        this.state.isAddingChannel = true;
    }

    doMobileNewMessage() {
        this.state.isAddingChat = true;
    }

    /**
     * @return {boolean}
     */
    hasActiveThreadMessages() {
        if (!this.storeProps.activeThreadCache) {
            return false;
        }
        return this.storeProps.activeThreadCache.messageLocalIds.length > 0;
    }

    /**
     * @param {Array} domain
     */
    updateDomain(domain) {
        this.storeDispatch('updateDiscuss', { domain });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _cancelReplyingToMessage() {
        this.state.isReplyingToMessage = false;
        this.state.replyingToMessageCounter = 0;
        this.state.replyingToMessageMessageLocalId = undefined;
        this.state.replyingToMessageThreadLocalId = undefined;
    }

    /**
     * @private
     */
    _clearAddingItem() {
        this.state.isAddingChannel = false;
        this.state.isAddingChat = false;
        this._addingChannelValue = '';
    }

    /**
     * @private
     * @param {string} threadLocalId
     */
    _openThread(threadLocalId) {
        if (
            !this.storeProps.isMobile &&
            this.storeProps.activeThreadCache &&
            this.storeProps.activeThreadCache.isLoaded &&
            this.storeProps.activeThreadCache.messageLocalIds.length > 0
        ) {
            const scrollTop = this._threadRef.comp.getScrollTop();
            if (typeof scrollTop === 'number') {
                this.state.threadCachesStoredScrollTop[this.storeProps.activeThreadCacheLocalId] = {
                    value: scrollTop,
                };
            }
        }
        if (this.state.isReplyingToMessage) {
            this._cancelReplyingToMessage();
        }
        this.storeDispatch('updateDiscuss', {
            activeThreadLocalId: threadLocalId,
        });
        this.storeDispatch('openThread', threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAddChannelAutocompleteSelect(ev, ui) {
        if (ui.item.special) {
            this.storeDispatch('createChannel', {
                name: this._addingChannelValue,
                public: ui.item.special,
                type: 'channel'
            });
        } else {
            this.storeDispatch('joinChannel', ui.item.id, { autoselect: true });
        }
        this._clearAddingItem();
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    async _onAddChannelAutocompleteSource(req, res) {
        const value = _.escape(req.term);
        this._addingChannelValue = value;
        const result = await this.env.rpc({
            model: 'mail.channel',
            method: 'channel_search_to_join',
            args: [value],
        });
        const items = result.map(data => {
            let escapedName = _.escape(data.name);
            return Object.assign(data, {
                label: escapedName,
                value: escapedName
            });
        });
        items.push({
            label: this.env.qweb.renderToString(
                'mail.component.Discuss.AutocompleteChannelPublicItem',
                { searchVal: value }
            ),
            value,
            special: 'public'
        }, {
            label: this.env.qweb.renderToString(
                'mail.component.Discuss.AutocompleteChannelPrivateItem',
                { searchVal: value }
            ),
            value,
            special: 'private'
        });
        res(items);
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAddChatAutocompleteSelect(ev, ui) {
        const partnerId = ui.item.id;
        // AKU FIXME: should not use hard-coded local id...
        const chat = this.storeGetters.chatFromPartner(`res.partner_${partnerId}`);
        if (chat) {
            this._openThread(chat.localId);
        } else {
            this.storeDispatch('createChannel', {
                autoselect: true,
                partnerId,
                type: 'chat'
            });
        }
        this._clearAddingItem();
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAddChatAutocompleteSource(req, res) {
        const value = _.escape(req.term);
        this.storeDispatch('searchPartners', {
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: this.storeGetters.partnerName(partner.localId),
                        label: this.storeGetters.partnerName(partner.localId),
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: value,
            limit: 10,
        });
    }

    /**
     * @private
     */
    _onHideMobileAddItemHeader() {
        this._clearAddingItem();
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileAddItemHeaderInputSelect(ev, ui) {
        if (this.state.isAddingChannel) {
            this._onAddChannelAutocompleteSelect(ev, ui);
        } else {
            this._onAddChatAutocompleteSelect(ev, ui);
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileAddItemHeaderInputSource(req, res) {
        if (this.state.isAddingChannel) {
            this._onAddChannelAutocompleteSource(req, res);
        } else {
            this._onAddChatAutocompleteSource(req, res);
        }
    }

    /**
     * TODO: almost duplicate code with
     *
     *  - ChatWindowManager._onRedirect()
     *
     * @private
     * @param {Event} ev
     * @param {Object} ev.detail
     * @param {integer} ev.detail.id
     * @param {string} ev.detail.model
     */
    _onRedirect(ev) {
        this.storeDispatch('redirect', {
            id: ev.detail.id,
            model: ev.detail.model,
        });
    }

    /**
     * @private
     */
    _onReplyingToMessageComposerDiscarded() {
        this._cancelReplyingToMessage();
    }

    /**
     * @private
     */
    _onReplyingToMessageMessagePosted() {
        this.env.do_notify(
            _.str.sprintf(
                this.env._t(`Message posted on "%s"`),
                this.storeGetters.threadName(this.state.replyingToMessageThreadLocalId)
            )
        );
        this._cancelReplyingToMessage();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.messageLocalId
     */
    _onReplyMessage(ev) {
        const { messageLocalId } = ev.detail;
        if (this.state.replyingToMessageMessageLocalId === messageLocalId) {
            this._cancelReplyingToMessage();
        } else {
            this.state.isReplyingToMessage = true;
            this.state.replyingToMessageCounter++;
            this.state.replyingToMessageMessageLocalId = messageLocalId;
            this.state.replyingToMessageThreadLocalId =
                this.env.store.state.messages[messageLocalId].originThreadLocalId;
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        const { tabId } = ev.detail;
        if (this.storeProps.activeMobileNavbarTabId === tabId) {
            return;
        }
        this._cancelReplyingToMessage();
        this.storeDispatch('updateDiscuss', {
            activeMobileNavbarTabId: tabId,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.threadLocalId
     */
    _onSelectThread(ev) {
        this._openThread(ev.detail.threadLocalId);
    }

    /**
     * @private
     */
    _onSidebarAddingChannel() {
        this.state.isAddingChannel = true;
    }

    /**
     * @private
     */
    _onSidebarAddingChat() {
        this.state.isAddingChat = true;
    }

    /**
     * @private
     */
    _onSidebarCancelAddingItem() {
        this._clearAddingItem();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onThreadRendered(ev) {
        this.trigger('o-update-control-panel');
    }
}

Object.assign(Discuss, {
    components: {
        AutocompleteInput,
        Composer,
        MobileMailboxSelection,
        MobileNavbar,
        Sidebar,
        Thread,
        ThreadPreviewList,
    },
    props: {
        initActiveThreadLocalId: String,
    },
    template: 'mail.component.Discuss',
});

return Discuss;

});
