odoo.define('mail.component.DiscussSidebar', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const SidebarItem = require('mail.component.DiscussSidebarItem');

const { Component, useState } = owl;
const { useGetters, useRef, useStore } = owl.hooks;

class DiscussSidebar extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({ quickSearchValue: "" });
        this.storeGetters = useGetters();
        this.storeProps = useStore(() => {
            return {
                pinnedChannelList: this.storeGetters.pinnedChannelList(),
                pinnedChatList: this.storeGetters.pinnedChatList(),
                pinnedMailboxList: this.storeGetters.pinnedMailboxList(),
                pinnedMailChannelAmount: this.storeGetters.pinnedMailChannelAmount(),
            };
        });
        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        this._quickSearchRef = useRef('quickSearch');
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * Return the list of channels that match the quick search value input.
     *
     * @return {mail.store.model.Thread[]}
     */
    get quickSearchChannelList() {
        if (!this.state.quickSearchValue) {
            return this.storeProps.pinnedChannelList;
        }
        const qsVal = this.state.quickSearchValue.toLowerCase();
        return this.storeProps.pinnedChannelList.filter(channel => {
            const nameVal = this.storeGetters.threadName(channel.localId).toLowerCase();
            return nameVal.indexOf(qsVal) !== -1;
        });
    }

    /**
     * Return the list of chats that match the quick search value input.
     *
     * @return {mail.store.model.Thread[]}
     */
    get quickSearchChatList() {
        if (!this.state.quickSearchValue) {
            return this.storeProps.pinnedChatList;
        }
        const qsVal = this.state.quickSearchValue.toLowerCase();
        return this.storeProps.pinnedChatList.filter(chat => {
            const nameVal = this.storeGetters.threadName(chat.localId).toLowerCase();
            return nameVal.indexOf(qsVal) !== -1;
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on add channel icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelAdd(ev) {
        this.trigger('o-discuss-adding-channel');
    }

    /**
     * Called when clicking on channel title.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelTitle(ev) {
        return this.env.do_action({
            name: this.env._t("Public Channels"),
            type: 'ir.actions.act_window',
            res_model: 'mail.channel',
            views: [[false, 'kanban'], [false, 'form']],
            domain: [['public', '!=', 'private']]
        });
    }

    /**
     * Called when clicking on add chat icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChatAdd(ev) {
        this.trigger('o-discuss-adding-chat');
    }

    /**
     * Called when clicking on a item: select the thread of this item as
     * discuss active thread. AKU TODO: maybe turn this into store dispatch?
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.threadLocalId
     */
    _onClickedItem(ev) {
        return this.trigger('o-select-thread', {
            threadLocalId: ev.detail.threadLocalId,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        this.trigger('o-discuss-cancel-adding-item');
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputQuickSearch(ev) {
        this.state.quickSearchValue = this._quickSearchRef.el.value;
    }
}

DiscussSidebar.components = { AutocompleteInput, SidebarItem };

DiscussSidebar.props = {
    activeThreadLocalId: {
        type: String,
        optional: true,
    },
    isAddingChannel: Boolean,
    isAddingChat: Boolean,
    onAddChannelAutocompleteSelect: Function,
    onAddChannelAutocompleteSource: Function,
    onAddChatAutocompleteSelect: Function,
    onAddChatAutocompleteSource: Function,
};

DiscussSidebar.template = 'mail.component.DiscussSidebar';

return DiscussSidebar;

});
