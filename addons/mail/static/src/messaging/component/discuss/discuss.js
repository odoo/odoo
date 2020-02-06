odoo.define('mail.messaging.component.Discuss', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail.messaging.component.AutocompleteInput'),
    Composer: require('mail.messaging.component.Composer'),
    DiscussMobileMailboxSelection: require('mail.messaging.component.DiscussMobileMailboxSelection'),
    DiscussSidebar: require('mail.messaging.component.DiscussSidebar'),
    MobileMessagingNavbar: require('mail.messaging.component.MobileMessagingNavbar'),
    ModerationDiscardDialog: require('mail.messaging.component.ModerationDiscardDialog'),
    ModerationRejectDialog: require('mail.messaging.component.ModerationRejectDialog'),
    NotificationList: require('mail.messaging.component.NotificationList'),
    ThreadViewer: require('mail.messaging.component.ThreadViewer'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class Discuss extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const discuss = this.env.messaging.discuss;
            return {
                checkedMessages: discuss.threadViewer.checkedMessages,
                discuss,
                isDeviceMobile: this.env.messaging.device.isMobile,
                isMessagingInitialized: this.env.messaging.isInitialized,
                thread: discuss.thread,
                threadCache: discuss.threadViewer.threadCache,
                uncheckedMessages: discuss.threadViewer.uncheckedMessages,
            };
        }, {
            compareDepth: {
                checkedMessages: 1,
                uncheckedMessages: 1,
            },
        });
        this._updateLocalStoreProps();
        /**
         * Reference of the thread. Useful to update scroll position correctly
         * on patch. AKU TODO: this made sense when composer was outside of
         * thread, but this may no longer be necessary??
         */
        this._threadRef = useRef('thread');

        // bind since passed as props
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
    }

    mounted() {
        this.discuss.update({ isOpen: true });
        if (this.discuss.thread) {
            this.trigger('o-push-state-action-manager');
        } else if (this.env.messaging.isInitialized) {
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
            this.discuss.thread.id === 'inbox' &&
            this._lastThreadCache === this.discuss.threadViewer.threadCache.localId &&
            this._lastThreadCounter > 0 && this.discuss.thread.counter === 0
        ) {
            this.trigger('o-show-rainbow-man');
        }
        this._activeThreadCache = this.discuss.threadViewer.threadCache;
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
     * @returns {mail.messaging.entity.Discuss}
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
            this.discuss.threadViewer.threadCache &&
            this.discuss.threadViewer.threadCache.localId
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
        this.env.do_notify(
            _.str.sprintf(
                this.env._t(`Message posted on "%s"`),
                this.discuss.replyingToMessage.originThread.displayName
            )
        );
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
     * @param {Object} ev.detail
     * @param {string} ev.detail.thread
     */
    _onSelectThread(ev) {
        this.discuss.update({ thread: ev.detail.thread });
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
    template: 'mail.messaging.component.Discuss',
});

return Discuss;

});
