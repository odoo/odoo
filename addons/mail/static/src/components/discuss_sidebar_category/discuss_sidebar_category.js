/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;


export class DiscussSidebarCategory extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        // bind since passed as props
        this._onAddItemAutocompleteSelect = this._onAddItemAutocompleteSelect.bind(this);
        this._onAddItemAutocompleteSource = this._onAddItemAutocompleteSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss_sidebar_category}
     */
    get category() {
        return this.messaging.models['mail.discuss_sidebar_category'].get(this.props.categoryLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAddItemAutocompleteSelect(ev, ui) {
        this.category._onAddItemAutocompleteSelect(ev, ui);
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAddItemAutocompleteSource(req, res) {
        this.category._onAddItemAutocompleteSource(req, res);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickView(ev) {
        ev.stopPropagation();
        return this.category._onClickViewCommand();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAdd(ev) {
        ev.stopPropagation();
        this.category.update({ isAddingItem: true });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        ev.stopPropagation();
        this.category.update({ isAddingItem: false });
    }

    /**
     * @private
     */
    _toggleCategoryOpen() {
        this.category._onClick();
    }
}

Object.assign(DiscussSidebarCategory, {
    props: {
        categoryLocalId: String,
    },
    template: 'mail.DiscussSidebarCategory',
});

registerMessagingComponent(DiscussSidebarCategory);
