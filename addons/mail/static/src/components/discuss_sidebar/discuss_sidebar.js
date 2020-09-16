odoo.define('mail/static/src/components/discuss_sidebar/discuss_sidebar.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    DiscussSidebarItem: require('mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class DiscussSidebar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();

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
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.__mfield_discuss(this);
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
            .all(thread =>
                thread.__mfield_isPinned(this) &&
                thread.__mfield_model(this) === 'mail.box'
            )
            .sort((mailbox1, mailbox2) => {
                if (mailbox1 === this.env.messaging.__mfield_inbox(this)) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.__mfield_inbox(this)) {
                    return 1;
                }
                if (mailbox1 === this.env.messaging.__mfield_starred(this)) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.__mfield_starred(this)) {
                    return 1;
                }
                const mailbox1Name = mailbox1.__mfield_displayName(this);
                const mailbox2Name = mailbox2.__mfield_displayName(this);
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
                thread.__mfield_channel_type() === 'chat' &&
                thread.__mfield_isPinned() &&
                thread.__mfield_model() === 'mail.channel'
            )
            .sort((c1, c2) =>
                c1.__mfield_displayName(this) < c2.__mfield_displayName(this) ? -1 : 1
            );
        if (!this.discuss.__mfield_sidebarQuickSearchValue(this)) {
            return allOrderedAndPinnedChats;
        }
        const qsVal = this.discuss.__mfield_sidebarQuickSearchValue(this).toLowerCase();
        return allOrderedAndPinnedChats.filter(chat => {
            const nameVal = chat.__mfield_displayName(this).toLowerCase();
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
                thread.__mfield_channel_type() === 'channel' &&
                thread.__mfield_isPinned() &&
                thread.__mfield_model() === 'mail.channel'
            )
            .sort((c1, c2) =>
                c1.__mfield_displayName(this) < c2.__mfield_displayName(this) ? -1 : 1
            );
        if (!this.discuss.__mfield_sidebarQuickSearchValue(this)) {
            return allOrderedAndPinnedMultiUserChannels;
        }
        const qsVal = this.discuss.__mfield_sidebarQuickSearchValue(this).toLowerCase();
        return allOrderedAndPinnedMultiUserChannels.filter(channel => {
            const nameVal = channel.__mfield_displayName(this).toLowerCase();
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
            this._quickSearchInputRef.el.value = this.discuss.__mfield_sidebarQuickSearchValue(this);
        }
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
        this.discuss.update({ __mfield_isAddingChannel: true });
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
        this.discuss.update({ __mfield_isAddingChat: true });
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
            __mfield_sidebarQuickSearchValue: this._quickSearchInputRef.el.value,
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
