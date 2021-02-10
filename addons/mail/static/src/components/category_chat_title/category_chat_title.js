odoo.define('mail/static/src/components/category_chat_title/category_chat_title.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    CategoryTitle: require('mail/static/src/components/category_title/category_title.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class CategoryChatTitle extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const discuss = this.env.messaging.discuss;
            return {
                allPinnedAndSortedChatTypeThreads: discuss && discuss.allPinnedAndSortedChatTypeThreads,
                discussIsAddingChat: discuss && discuss.isAddingChat,
                isCategoryOpen: discuss && discuss.categoryChat.isOpen,
            }
        });

        this._onAddChatAutocompleteSelect = this._onAddChatAutocompleteSelect.bind(this);
        this._onAddChatAutocompleteSource = this._onAddChatAutocompleteSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get FIND_OR_START_CONVERSATION() {
        return this.env._t("Find or start a conversation...");
    }

    get category() {
        return this.discuss && this.discuss.categoryChat;
    }

    get discuss() {
        return this.env.messaging.discuss;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChatAdd(ev) {
        ev.stopPropagation();
        this.discuss.update({ isAddingChat: true });
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
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }
}

Object.assign(CategoryChatTitle, {
    components,
    props: {},
    template: 'mail.CategoryChatTitle',
});

return CategoryChatTitle;

});
