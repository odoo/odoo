/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { AutocompleteInput } from '@mail/components/autocomplete_input/autocomplete_input';
import { DiscussSidebarCategoryItem } from '@mail/components/discuss_sidebar_category_item/discuss_sidebar_category_item';

const { Component } = owl;

const components = { AutocompleteInput, DiscussSidebarCategoryItem };

export class DiscussSidebarCategory extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
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
        return this.env.models['mail.discuss_sidebar_category'].get(this.props.categoryLocalId);
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
    components,
    props: {
        categoryLocalId: String,
    },
    template: 'mail.DiscussSidebarCategory',
});
