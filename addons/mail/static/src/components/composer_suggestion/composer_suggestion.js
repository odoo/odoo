/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import useUpdate from '@mail/component_hooks/use_update/use_update';
import PartnerImStatusIcon from '@mail/components/partner_im_status_icon/partner_im_status_icon';

const { Component } = owl;

const components = { PartnerImStatusIcon };

// TODO SEB rename to just suggestion
class ComposerSuggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const suggestionListItem = this.env.models['mail.suggestion_list_item'].get(props.suggestionListItemLocalId);
            return {
                suggestionListItem: suggestionListItem && suggestionListItem.__state,
            };
        });
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.suggestion_list_item}
     */
    get suggestionListItem() {
        return this.env.models['mail.suggestion_list_item'].get(this.props.suggestionListItemLocalId);
    }

    /**
     * Returns a descriptive title for this suggestion list item. Useful to be
     * able to read both parts when they are overflowing the UI.
     *
     * @returns {string}
     */
    title() {
        if (!this.suggestionListItem) {
            return '';
        }
        if (!this.suggestionListItem.namePart2) {
            return this.suggestionListItem.namePart1;
        }
        return _.str.sprintf("%s: %s", this.suggestionListItem.namePart1, this.suggestionListItem.namePart2);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (!this.suggestionListItem) {
            return;
        }
        if (this.suggestionListItem.hasToScrollIntoView) {
            this.el.scrollIntoView({
                block: 'center',
            });
            this.suggestionListItem.update({ hasToScrollIntoView: false });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClick(ev) {
        if (!this.suggestionListItem) {
            return;
        }
        this.suggestionListItem.onClickSuggestion(ev);
        // This event is used to focus the composer. It cannot be removed until
        // there is one composer model per composer component.
        this.trigger('o-composer-suggestion-clicked');
    }

}

Object.assign(ComposerSuggestion, {
    components,
    props: {
        suggestionListItemLocalId: String,
    },
    template: 'mail.ComposerSuggestion',
});

export default ComposerSuggestion;
