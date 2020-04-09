odoo.define('mail.messaging.component.DiscussSidebar', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail.messaging.component.AutocompleteInput'),
    DiscussSidebarItem: require('mail.messaging.component.DiscussSidebarItem'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class DiscussSidebar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(
            (...args) => this._useStoreSelector(...args),
            { compareDepth: () => this._useStoreCompareDepth() }
        );

        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        this._quickSearchInputRef = useRef('quickSearchInput');

        // bind since passed as props
        this._onAddChannelAutocompleteSelect = this._onAddChannelAutocompleteSelect.bind(this);
        this._onAddChannelAutocompleteSource = this._onAddChannelAutocompleteSource.bind(this);
        this._onAddChatAutocompleteSelect = this._onAddChatAutocompleteSelect.bind(this);
        this._onAddChatAutocompleteSource = this._onAddChatAutocompleteSource.bind(this);
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * Return the list of chats that match the quick search value input.
     *
     * @returns {mail.messaging.entity.Thread[]}
     */
    get quickSearchPinnedAndOrderedChats() {
        const allOrderedAndPinnedChats =
            this.env.entities.Thread.allOrderedAndPinnedChats;
        if (!this.discuss.sidebarQuickSearchValue) {
            return allOrderedAndPinnedChats;
        }
        const qsVal = this.discuss.sidebarQuickSearchValue.toLowerCase();
        return allOrderedAndPinnedChats.filter(chat => {
            const nameVal = chat.displayName.toLowerCase();
            return nameVal.includes(qsVal);
        });
    }

    /**
     * Return the list of channels that match the quick search value input.
     *
     * @returns {mail.messaging.entity.Thread[]}
     */
    get quickSearchOrderedAndPinnedMultiUserChannels() {
        const allOrderedAndPinnedMultiUserChannels =
            this.env.entities.Thread.allOrderedAndPinnedMultiUserChannels;
        if (!this.discuss.sidebarQuickSearchValue) {
            return allOrderedAndPinnedMultiUserChannels;
        }
        const qsVal = this.discuss.sidebarQuickSearchValue.toLowerCase();
        return allOrderedAndPinnedMultiUserChannels.filter(channel => {
            const nameVal = channel.displayName.toLowerCase();
            return nameVal.includes(qsVal);
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this._quickSearchInputRef.el) {
            this._quickSearchInputRef.el.value = this.discuss.sidebarQuickSearchValue;
        }
    }

    /**
     * @private
     * @returns {Object}
     */
    _useStoreCompareDepth() {
        return {
            allOrderedAndPinnedChats: 1,
            allOrderedAndPinnedMailboxes: 1,
            allOrderedAndPinnedMultiUserChannels: 1,
            allPinnedChannelAmount: 1,
        };
    }

    /**
     * @private
     * @param {Object} props
     * @returns {Object}
     */
    _useStoreSelector(props) {
        const Thread = this.env.entities.Thread;
        return {
            allOrderedAndPinnedChats: Thread.allOrderedAndPinnedChats,
            allOrderedAndPinnedMailboxes: Thread.allOrderedAndPinnedMailboxes,
            allOrderedAndPinnedMultiUserChannels: Thread.allOrderedAndPinnedMultiUserChannels,
            allPinnedChannelAmount: Thread.allPinnedChannels.length,
            discuss: this.env.messaging.discuss,
        };
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
        this.discuss.handleAddChannelAutocompleteSelect(ev, ui);
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAddChannelAutocompleteSource(req, res) {
        this.discuss.handleAddChannelAutocompleteSource(req, res);
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAddChatAutocompleteSelect(ev, ui) {
        this.discuss.handleAddChatAutocompleteSelect(ev, ui);
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAddChatAutocompleteSource(req, res) {
        this.discuss.handleAddChatAutocompleteSource(req, res);
    }

    /**
     * Called when clicking on add channel icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelAdd(ev) {
        ev.stopPropagation();
        this.discuss.update({ isAddingChannel: true });
    }

    /**
     * Called when clicking on channel title.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelTitle(ev) {
        ev.stopPropagation();
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
        ev.stopPropagation();
        this.discuss.update({ isAddingChat: true });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputQuickSearch(ev) {
        ev.stopPropagation();
        this.discuss.update({ sidebarQuickSearchValue: this._quickSearchInputRef.el.value });
    }

}

Object.assign(DiscussSidebar, {
    components,
    props: {},
    template: 'mail.messaging.component.DiscussSidebar',
});

return DiscussSidebar;

});
