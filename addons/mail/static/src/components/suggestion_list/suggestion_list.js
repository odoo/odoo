/** @odoo-module **/

import ComposerSuggestion from '@mail/components/composer_suggestion/composer_suggestion';
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;

const components = { ComposerSuggestion };

class SuggestionList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const suggestionList = this.env.models['mail.suggestion_list'].get(props.suggestionListLocalId);
            const extraSuggestionListItems = suggestionList ? suggestionList.extraSuggestionListItems : [];
            const mainSuggestionListItems = suggestionList ? suggestionList.mainSuggestionListItems : [];
            return {
                extraSuggestionListItems,
                mainSuggestionListItems,
            };
        }, {
            compareDepth: {
                extraSuggestionListItems: 1,
                mainSuggestionListItems: 1,
            },
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.suggestion_list}
     */
    get suggestionList() {
        return this.env.models['mail.suggestion_list'].get(this.props.suggestionListLocalId);
    }

}

Object.assign(SuggestionList, {
    components,
    defaultProps: {
        isBelow: false,
    },
    props: {
        isBelow: Boolean,
        suggestionListLocalId: String,
    },
    template: 'mail.SuggestionList',
});

export default SuggestionList;
