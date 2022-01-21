odoo.define('mail/static/src/components/discuss_sidebar/discuss_sidebar.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    DiscussSidebarItem: require('mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class DiscussSidebar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(
            (...args) => this._useStoreSelector(...args),
            { compareDepth: this._useStoreCompareDepth() }
        );
        useUpdate({ func: () => this._update() });
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {string}
     */
    get FIND_OR_CREATE_CHANNEL() {
        return this.env._t("Find or create a channel...");
    }

    /**
     * @returns {mail.thread[]}
     */
    get orderedMailboxes() {
        return this.env.models['mail.thread']
            .all(thread => thread.isPinned && thread.model === 'mail.box')
            .sort((mailbox1, mailbox2) => {
                if (mailbox1 === this.env.messaging.inbox) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.inbox) {
                    return 1;
                }
                if (mailbox1 === this.env.messaging.starred) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.starred) {
                    return 1;
                }
                const mailbox1Name = mailbox1.displayName;
                const mailbox2Name = mailbox2.displayName;
                mailbox1Name < mailbox2Name ? -1 : 1;
            });
    }

    /**
     * Return the list of chats that match the quick search value input.
     *
     * @returns {mail.thread[]}
     */
    get quickSearchPinnedAndOrderedChats() {
        const allOrderedAndPinnedChats = this.env.models['mail.thread']
            .all(thread =>
                thread.channel_type === 'chat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            )
            .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
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
     * @returns {mail.thread[]}
     */
    get quickSearchOrderedAndPinnedMultiUserChannels() {
        const allOrderedAndPinnedMultiUserChannels = this.env.models['mail.thread']
            .all(thread =>
                thread.channel_type === 'channel' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            )
            .sort((c1, c2) => {
                if (c1.displayName && !c2.displayName) {
                    return -1;
                } else if (!c1.displayName && c2.displayName) {
                    return 1;
                } else if (c1.displayName && c2.displayName && c1.displayName !== c2.displayName) {
                    return c1.displayName.toLowerCase() < c2.displayName.toLowerCase() ? -1 : 1;
                } else {
                    return c1.id - c2.id;
                }
            });
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
        if (!this.discuss) {
            return;
        }
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
        };
    }

    /**
     * @private
     * @param {Object} props
     * @returns {Object}
     */
    _useStoreSelector(props) {
        const discuss = this.env.messaging.discuss;
        return {
            allOrderedAndPinnedChats: this.quickSearchPinnedAndOrderedChats,
            allOrderedAndPinnedMailboxes: this.orderedMailboxes,
            allOrderedAndPinnedMultiUserChannels: this.quickSearchOrderedAndPinnedMultiUserChannels,
            allPinnedChannelAmount:
                this.env.models['mail.thread']
                .all(thread =>
                    thread.isPinned &&
                    thread.model === 'mail.channel'
                ).length,
            discussIsAddingChannel: discuss && discuss.isAddingChannel,
            discussIsAddingChat: discuss && discuss.isAddingChat,
            discussSidebarQuickSearchValue: discuss && discuss.sidebarQuickSearchValue,
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
        return this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Public Channels"),
                type: 'ir.actions.act_window',
                res_model: 'mail.channel',
                views: [[false, 'kanban'], [false, 'form']],
                domain: [['public', '!=', 'private']]
            },
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
        this.discuss.update({
            sidebarQuickSearchValue: this._quickSearchInputRef.el.value,
        });
    }

}

Object.assign(DiscussSidebar, {
    components,
    props: {},
    template: 'mail.DiscussSidebar',
});

return DiscussSidebar;

});
