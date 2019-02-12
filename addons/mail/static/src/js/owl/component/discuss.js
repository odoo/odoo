odoo.define('mail.component.Discuss', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const Composer = require('mail.component.Composer');
const MobileMailboxSelection = require('mail.component.DiscussMobileMailboxSelection');
const Sidebar = require('mail.component.DiscussSidebar');
const MobileNavbar = require('mail.component.MobileMessagingNavbar');
const Thread = require('mail.component.Thread');
const ThreadPreviewList = require('mail.component.ThreadPreviewList');

class Discuss extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.DEBUG = true;
        this.id = _.uniqueId('o_discuss_');
        this.state = owl.useState({
            isAddingChannel: false,
            isAddingChat: false,
            isReplyingToMessage: false,
            replyingToMessageCounter: 0,
            replyingToMessageMessageLocalId: null,
            replyingToMessageThreadLocalId: null,
            threadCachesStoredScrollTop: {}, // key: threadCachelocalId, value: { value } (obj. to prevent 0 being falsy)
        });
        this._addingChannelValue = "";
        this._globalCaptureClickEventListener = ev => this._onClickCaptureGlobal(ev);
        /**
         * Locally tracked store props `activeThreadCacheLocalId`.
         * Useful to-set scroll position from last stored one.
         */
        this._activeThreadCacheLocalId = null;
        /**
         * Locally tracked store props `inboxMarkAsReadCounter`.
         */
        this._inboxMarkAsReadCounter = 0;
        this._replyingToMessageComposerRef = owl.hooks.useRef('replyingToMessageComposer');
        /**
         * Tracked last targeted thread. Used to determine whether it should
         * autoscroll and style target thread, in either sidebar or in mobile.
         */
        this._targetThreadCounter = 0;
        this._targetThreadLocalId = null;
        this._threadRef = owl.hooks.useRef('thread');
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

        // bind since passed as props
        this._onAddChannelAutocompleteSelect = this._onAddChannelAutocompleteSelect.bind(this);
        this._onAddChannelAutocompleteSource = this._onAddChannelAutocompleteSource.bind(this);
        this._onAddChatAutocompleteSelect = this._onAddChatAutocompleteSelect.bind(this);
        this._onAddChatAutocompleteSource = this._onAddChatAutocompleteSource.bind(this);
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);

        if (this.DEBUG) {
            window.discuss = this;
        }
    }

    mounted() {
        document.addEventListener('click', this._globalCaptureClickEventListener, true);
        this.dispatch('updateDiscuss', {
            isOpen: true,
        });
        if (this.storeProps.activeThreadLocalId) {
            this.trigger('o-push-state-action-manager', {
                activeThreadLocalId: this.props.initActiveThreadLocalId,
            });
        } else {
            this.dispatch('openThread', this.props.initActiveThreadLocalId, {
                resetDiscussDomain: true,
            });
        }
        this._activeThreadCacheLocalId = this.storeProps.activeThreadCacheLocalId;
    }

    /**
     * AKU TODO: move this code to patched() hook
     *
     * @param {Object} nextStoreProps
     * @param {Object} [nextStoreProps.activeThread]
     * @param {integer} [nextStoreProps.activeThreadCounter]
     */
    willUpdateProps(nextStoreProps) {
        const activeThread = this.storeProps.activeThread;
        if (!activeThread) {
            return;
        }
        if (nextStoreProps.activeThreadLocalId !== this.storeProps.activeThreadLocalId) {
            this.trigger('o-push-state-action-manager', {
                activeThreadLocalId: nextStoreProps.activeThreadLocalId,
            });
        }
    }

    willPatch() {
        const shouldFocusReplyComposer =
            this.state.isReplyingToMessage &&
            (
                !this._wp.isReplyingToMessage ||
                this._wp.replyingToMessageCounter !==
                    this.state.replyingToMessageCounter
            );
        Object.assign(this._wp, {
            isReplyingToMessage: this.state.isReplyingToMessage,
            replyingToMessageCounter: this.state.replyingToMessageCounter,
        });
        this._willPatchSnapshot = {
            shouldFocusReplyComposer,
        };
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
        this._targetThreadCounter = this.storeProps.targetThreadCounter;
        this._targetThreadLocalId = this.storeProps.targetThreadLocalId;
        if (this._inboxMarkAsReadCounter < this.storeProps.inboxMarkAsReadCounter) {
            this.trigger('o-show-rainbow-man');
        }
        this._activeThreadCacheLocalId = this.storeProps.activeThreadCacheLocalId;
        this._inboxMarkAsReadCounter = this.storeProps.inboxMarkAsReadCounter;
        this._willPatchSnapshot = {};
    }

    willUnmount() {
        document.removeEventListener('click', this._globalCaptureClickEventListener, true);
        this.dispatch('closeDiscuss');
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
        this.dispatch('updateDiscuss', {
            domain,
        });
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
        this.state.replyingToMessageMessageLocalId = null;
        this.state.replyingToMessageThreadLocalId = null;
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
        if (
            !this.storeProps.isMobile &&
            this.storeProps.activeThreadCache &&
            this._threadRef.comp.props.hasComposer
        ) {
            this.dispatch('updateDiscuss', {
                storedThreadComposers: {
                    ...this.storeProps.storedThreadComposers,
                    [this.storeProps.activeThreadLocalId]: this._threadRef.comp.getComposerState(),
                },
            });
        }
        if (this.state.isReplyingToMessage) {
            this._cancelReplyingToMessage();
        }
        this.dispatch('updateDiscuss', {
            activeThreadLocalId: threadLocalId,
        });
        this.dispatch('openThread', threadLocalId, {
            markAsDiscussTarget: true,
        });
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
            this.dispatch('createChannel', {
                name: this._addingChannelValue,
                public: ui.item.special,
                type: 'channel'
            });
        } else {
            this.dispatch('joinChannel', ui.item.id, { autoselect: true });
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
            label:
                this
                    .env
                    .qweb
                    .renderToString('mail.component.Discuss.AutocompleteChannelPublicItem', {
                        searchVal: value,
                    }),
            value,
            special: 'public'
        }, {
            label:
                this
                    .env
                    .qweb
                    .renderToString('mail.component.Discuss.AutocompleteChannelPrivateItem', {
                        searchVal: value,
                    }),
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
        const chat = this.env.store.getters.chatFromPartner(`res.partner_${partnerId}`);
        if (chat) {
            this._openThread(chat.localId);
        } else {
            this.dispatch('createChannel', {
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
        this.dispatch('searchPartners', {
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: this.env.store.getters.partnerName(partner.localId),
                        label: this.env.store.getters.partnerName(partner.localId),
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
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (
            (
                !this.storeProps.isMobile &&
                this.storeProps.targetThreadLocalId
            ) ||
            (
                this.storeProps.isMobile &&
                !this.env.store.getters.haveVisibleChatWindows()
            )
        ) {
            this.dispatch('updateDiscuss', {
                targetThreadLocalId: null,
            });
        }
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
        this.dispatch('redirect', {
            ev,
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
                this.env._t("Message posted on \"%s\""),
                this.env.store.getters.threadName(this.state.replyingToMessageThreadLocalId)));
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
        this.dispatch('updateDiscuss', {
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

Discuss.components = {
    AutocompleteInput,
    Composer,
    MobileMailboxSelection,
    MobileNavbar,
    Sidebar,
    Thread,
    ThreadPreviewList,
};

/**
 * @param {Object} state
 * @return {Object}
 */
Discuss.mapStoreToProps = function (state) {
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
    return {
        ...state.discuss,
        activeThread,
        activeThreadCache,
        activeThreadCacheLocalId,
        // intentionally keep unsynchronize value of old thread counter
        // useful in willUpdateProps to detect change of counter
        activeThreadCounter: activeThread && activeThread.counter,
        isMobile: state.isMobile,
    };
};

Discuss.props = {
    initActiveThreadLocalId: String,
};

Discuss.template = 'mail.component.Discuss';

return Discuss;

});
