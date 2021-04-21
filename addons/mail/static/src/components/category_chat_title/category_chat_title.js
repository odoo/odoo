/** @odoo-module **/

import useStore  from '@mail/component_hooks/use_store/use_store';
import AutocompleteInput from '@mail/components/autocomplete_input/autocomplete_input';
import CategoryTitle from '@mail/components/category_title/category_title';

const { Component } = owl;

const components = { AutocompleteInput, CategoryTitle };

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

export default CategoryChatTitle;
