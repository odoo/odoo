/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { link, unlink } from '@mail/model/model_field_command';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component } = owl;

export class Discuss extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._updateLocalStoreProps();
        // bind since passed as props
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
        useUpdate({ func: () => this._update() });
    }

    _update() {
        if (!this.discuss) {
            return;
        }
        this.discuss.update({ isOpen: true });
        if (this.discuss.thread) {
            this.trigger('o-push-state-action-manager');
        }
        if (
            this.discuss.thread &&
            this.discuss.thread === this.messaging.inbox &&
            this.discuss.threadView &&
            this._lastThreadCache === this.discuss.threadView.threadCache.localId &&
            this._lastThreadCounter > 0 && this.discuss.thread.counter === 0
        ) {
            this.trigger('o-show-rainbow-man');
        }
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
        return this.messaging && this.messaging.discuss;
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
        if (!this.discuss) {
            return;
        }
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        ev.stopPropagation();
        if (this.discuss.activeMobileNavbarTabId === ev.detail.tabId) {
            return;
        }
        this.discuss.update({ activeMobileNavbarTabId: ev.detail.tabId });
        if (
            this.discuss.activeMobileNavbarTabId === 'mailbox' &&
            (!this.discuss.thread || this.discuss.thread.model !== 'mailbox')
        ) {
            this.discuss.update({ thread: link(this.messaging.inbox) });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'mailbox') {
            this.discuss.update({ thread: unlink() });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'chat') {
            this.discuss.update({ isAddingChat: false });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'channel') {
            this.discuss.update({ isAddingChannel: false });
        }
    }

}

Object.assign(Discuss, {
    props: {},
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
