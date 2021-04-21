/** @odoo-module **/

import useStore from '@mail/component_hooks/use_store/use_store';
import AutocompleteInput from '@mail/components/autocomplete_input/autocomplete_input';
import CategoryTitle from '@mail/components/category_title/category_title';

const { Component } = owl;

const components = { AutocompleteInput, CategoryTitle };

class CategoryChannelTitle extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const discuss = this.env.messaging.discuss;
            return {
                allPinnedAndSortedChannelTypeThreads: discuss && discuss.allPinnedAndSortedChannelTypeThreads,
                discussIsAddingChat: discuss && discuss.isAddingChat,
                isCategoryOpen: discuss && discuss.categoryChannel.isOpen,
            }
        });

        this._onAddChannelAutocompleteSelect = this._onAddChannelAutocompleteSelect.bind(this);
        this._onAddChannelAutocompleteSource = this._onAddChannelAutocompleteSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get FIND_OR_CREATE_CHANNEL() {
        return this.env._t("Find or create a channel...");
    }

    get category() {
        return this.discuss && this.discuss.categoryChannel;
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
    _onClickChannelAdd(ev) {
        ev.stopPropagation();
        this.discuss.update({ isAddingChannel: true });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelsView(ev) {
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
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }
}

Object.assign(CategoryChannelTitle, {
    components,
    props: {},
    template: 'mail.CategoryChannelTitle',
});

export default CategoryChannelTitle;
