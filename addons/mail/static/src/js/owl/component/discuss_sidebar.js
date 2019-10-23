odoo.define('mail.component.DiscussSidebar', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const SidebarItem = require('mail.component.DiscussSidebarItem');

class DiscussSidebar extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = owl.useState({
            quickSearchValue: "",
        });
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore(() => {
            return {
                pinnedChannelList: this.storeGetters.pinnedChannelList(),
                pinnedChatList: this.storeGetters.pinnedChatList(),
                pinnedMailboxList: this.storeGetters.pinnedMailboxList(),
                pinnedMailChannelAmount: this.storeGetters.pinnedMailChannelAmount(),
            };
        });
        this._quickSearchRef = owl.hooks.useRef('quickSearch');
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
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
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string} threadLocalId
     * @return {boolean}
     */
    isItemPartiallyVisible(threadLocalId) {
        return this.__owl__.refs[threadLocalId].isPartiallyVisible({
            scrollable: this.el,
        });
    }

    /**
     * @param {string} threadLocalId
     */
    scrollToItem(threadLocalId) {
        this.__owl__.refs[threadLocalId].scrollIntoview();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelAdd(ev) {
        this.trigger('o-discuss-adding-channel');
    }

    /**
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
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChatAdd(ev) {
        this.trigger('o-discuss-adding-chat');
    }

    /**
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

DiscussSidebar.components = {
    AutocompleteInput,
    SidebarItem
};

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
