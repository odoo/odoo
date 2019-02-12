odoo.define('mail.component.MessagingMenu', function (require) {
"use strict";

const AutocompleteInput = require('mail.component.AutocompleteInput');
const MobileNavbar = require('mail.component.MobileMessagingNavbar');
const ThreadPreviewList = require('mail.component.ThreadPreviewList');

class MessagingMenu extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.DEBUG = true;
        this.id = _.uniqueId('o_messagingMenu_');

        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);

        if (this.DEBUG) {
            window.messaging_menu = this;
        }
        this._globalCaptureEventListener = ev => this._onClickCaptureGlobal(ev);
    }

    mounted() {
        document.addEventListener('click', this._globalCaptureEventListener, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._globalCaptureEventListener, true);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get mobileNewMessageInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @return {Object[]}
     */
    get tabs() {
        return [{
            icon: 'fa fa-envelope',
            id: 'all',
            label: this.env._t("All"),
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
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (
            this.storeProps.isMobile &&
            this.env.store.getters.haveVisibleChatWindows()
        ) {
            return;
        }
        if (ev.target === this.el) {
            return;
        }
        if (ev.target.closest(`[data-id="${this.id}"]`)) {
            return;
        }
        if (ev.target.closest(`.${this.id}_mobileNewMessageInputAutocomplete`)) {
            return;
        }
        this.dispatch('closeMessagingMenu');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDesktopTabButton(ev) {
        this.dispatch('updateMessagingMenu', {
            activeTabId: ev.currentTarget.dataset.tabId,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNewMessage(ev) {
        if (!this.storeProps.isMobile) {
            this.dispatch('openThread', 'new_message');
            this.dispatch('closeMessagingMenu');
        } else {
            this.dispatch('toggleMessagingMenuMobileNewMessage');
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggler(ev) {
        this.dispatch('toggleMessagingMenuOpen');
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideMobileNewMessage(ev) {
        ev.stopPropagation();
        this.dispatch('toggleMessagingMenuMobileNewMessage');
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileNewMessageInputSelect(ev, ui) {
        const partnerId = ui.item.id;
        const chat = this.env.store.getters.chatFromPartner(`res.partner_${partnerId}`);
        if (chat) {
            this.dispatch('openThread', chat.localId);
        } else {
            this.dispatch('createChannel', {
                autoselect: true,
                partnerId,
                type: 'chat'
            });
        }
        if (!this.storeProps.isMobile) {
            this.dispatch('closeMessagingMenu');
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
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
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        this.dispatch('updateMessagingMenu', {
            activeTabId: ev.detail.tabId,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.threadLocalId
     */
    _onSelectThread(ev) {
        this.dispatch('openThread', ev.detail.threadLocalId);
        if (!this.storeProps.isMobile) {
            this.dispatch('closeMessagingMenu');
        }
    }
}

MessagingMenu.components = {
    AutocompleteInput,
    MobileNavbar,
    ThreadPreviewList,
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {Object} getters
 * @return {Object}
 */
MessagingMenu.mapStoreToProps = function (state, ownProps, getters) {
    return {
        ...state.messagingMenu,
        counter: getters.globalThreadUnreadCounter(),
        isDiscussOpen: state.discuss.isOpen,
        isMobile: state.isMobile,
    };
};

MessagingMenu.template = 'mail.component.MessagingMenu';

return MessagingMenu;

});
