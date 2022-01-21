odoo.define('mail/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    Composer: require('mail/static/src/components/composer/composer.js'),
    DiscussMobileMailboxSelection: require('mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection.js'),
    DiscussSidebar: require('mail/static/src/components/discuss_sidebar/discuss_sidebar.js'),
    MobileMessagingNavbar: require('mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.js'),
    ModerationDiscardDialog: require('mail/static/src/components/moderation_discard_dialog/moderation_discard_dialog.js'),
    ModerationRejectDialog: require('mail/static/src/components/moderation_reject_dialog/moderation_reject_dialog.js'),
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const patchMixin = require('web.patchMixin');

const { Component } = owl;
const { useRef } = owl.hooks;

class Discuss extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore((...args) => this._useStoreSelector(...args), {
            compareDepth: {
                checkedMessages: 1,
                uncheckedMessages: 1,
            },
        });
        this._updateLocalStoreProps();
        /**
         * Reference of the composer. Useful to focus it.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the ThreadView. Useful to focus it.
         */
        this._threadViewRef = useRef('threadView');
        // bind since passed as props
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
    }

    mounted() {
        this.discuss.update({ isOpen: true });
        if (this.discuss.thread) {
            this.trigger('o-push-state-action-manager');
        } else if (this.env.isMessagingInitialized()) {
            this.discuss.openInitThread();
        }
        this._updateLocalStoreProps();
    }

    patched() {
        this.trigger('o-update-control-panel');
        if (this.discuss.thread) {
            this.trigger('o-push-state-action-manager');
        }
        if (
            this.discuss.thread &&
            this.discuss.thread === this.env.messaging.inbox &&
            this.discuss.threadView &&
            this._lastThreadCache === this.discuss.threadView.threadCache.localId &&
            this._lastThreadCounter > 0 && this.discuss.thread.counter === 0
        ) {
            this.trigger('o-show-rainbow-man');
        }
        this._activeThreadCache = this.discuss.threadView && this.discuss.threadView.threadCache;
        this._updateLocalStoreProps();
    }

    willUnmount() {
        if (this.discuss) {
            this.discuss.close();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    get addChannelInputPlaceholder() {
        return this.env._t("Create or search channel...");
    }

    /**
     * @returns {string}
     */
    get addChatInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {Object[]}
     */
    mobileNavbarTabs() {
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
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateLocalStoreProps() {
        /**
         * Locally tracked store props `activeThreadCache`.
         * Useful to set scroll position from last stored one and to display
         * rainbox man on inbox.
         */
        this._lastThreadCache = (
            this.discuss.threadView &&
            this.discuss.threadView.threadCache &&
            this.discuss.threadView.threadCache.localId
        );
        /**
         * Locally tracked store props `threadCounter`.
         * Useful to display the rainbow man on inbox.
         */
        this._lastThreadCounter = (
            this.discuss.thread &&
            this.discuss.thread.counter
        );
    }

    /**
     * Returns data selected from the store.
     *
     * @private
     * @param {Object} props
     * @returns {Object}
     */
    _useStoreSelector(props) {
        const discuss = this.env.messaging && this.env.messaging.discuss;
        const thread = discuss && discuss.thread;
        const threadView = discuss && discuss.threadView;
        const replyingToMessage = discuss && discuss.replyingToMessage;
        const replyingToMessageOriginThread = replyingToMessage && replyingToMessage.originThread;
        const checkedMessages = threadView ? threadView.checkedMessages : [];
        return {
            checkedMessages,
            checkedMessagesIsModeratedByCurrentPartner: checkedMessages && checkedMessages.some(message => message.isModeratedByCurrentPartner), // for widget
            discuss,
            discussActiveId: discuss && discuss.activeId, // for widget
            discussActiveMobileNavbarTabId: discuss && discuss.activeMobileNavbarTabId,
            discussHasModerationDiscardDialog: discuss && discuss.hasModerationDiscardDialog,
            discussHasModerationRejectDialog: discuss && discuss.hasModerationRejectDialog,
            discussIsAddingChannel: discuss && discuss.isAddingChannel,
            discussIsAddingChat: discuss && discuss.isAddingChat,
            discussIsDoFocus: discuss && discuss.isDoFocus,
            discussReplyingToMessageOriginThreadComposer: replyingToMessageOriginThread && replyingToMessageOriginThread.composer,
            inbox: this.env.messaging.inbox,
            isDeviceMobile: this.env.messaging && this.env.messaging.device.isMobile,
            isMessagingInitialized: this.env.isMessagingInitialized(),
            replyingToMessage,
            starred: this.env.messaging.starred, // for widget
            thread,
            threadCache: threadView && threadView.threadCache,
            threadChannelType: thread && thread.channel_type, // for widget
            threadDisplayName: thread && thread.displayName, // for widget
            threadCounter: thread && thread.counter,
            threadModel: thread && thread.model,
            threadPublic: thread && thread.public, // for widget
            threadView,
            threadViewMessagesLength: threadView && threadView.messages.length, // for widget
            uncheckedMessages: threadView ? threadView.uncheckedMessages : [], // for widget
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDialogClosedModerationDiscard() {
        this.discuss.update({ hasModerationDiscardDialog: false });
    }

    /**
     * @private
     */
    _onDialogClosedModerationReject() {
        this.discuss.update({ hasModerationRejectDialog: false });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onFocusinComposer(ev) {
        this.discuss.update({ isDoFocus: false });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideMobileAddItemHeader(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileAddItemHeaderInputSelect(ev, ui) {
        const discuss = this.discuss;
        if (discuss.isAddingChannel) {
            discuss.handleAddChannelAutocompleteSelect(ev, ui);
        } else {
            discuss.handleAddChatAutocompleteSelect(ev, ui);
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileAddItemHeaderInputSource(req, res) {
        if (this.discuss.isAddingChannel) {
            this.discuss.handleAddChannelAutocompleteSource(req, res);
        } else {
            this.discuss.handleAddChatAutocompleteSource(req, res);
        }
    }

    /**
     * @private
     */
    _onReplyingToMessageMessagePosted() {
        this.env.services['notification'].notify({
            message: _.str.sprintf(
                this.env._t(`Message posted on "%s"`),
                owl.utils.escape(this.discuss.replyingToMessage.originThread.displayName)
            ),
            type: 'warning',
        });
        this.discuss.clearReplyingToMessage();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        ev.stopPropagation();
        if (this.discuss.activeMobileNavbarTabId === ev.detail.tabId) {
            return;
        }
        this.discuss.clearReplyingToMessage();
        this.discuss.update({ activeMobileNavbarTabId: ev.detail.tabId });
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
    components,
    props: {},
    template: 'mail.Discuss',
});

return patchMixin(Discuss);

});
