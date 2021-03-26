/** @odoo-module **/

import ComposerSuggestion from '@mail/components/composer_suggestion/composer_suggestion';
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;

const components = { ComposerSuggestion };

class ComposerSuggestionList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(props.composerLocalId);
            const activeSuggestedRecord = composer
                ? composer.activeSuggestedRecord
                : undefined;
            const extraSuggestedRecords = composer
                ? composer.extraSuggestedRecords
                : [];
            const mainSuggestedRecords = composer
                ? composer.mainSuggestedRecords
                : [];
            return {
                activeSuggestedRecord,
                composer,
                composerSuggestionModelName: composer && composer.suggestionModelName,
                extraSuggestedRecords,
                mainSuggestedRecords,
            };
        }, {
            compareDepth: {
                extraSuggestedRecords: 1,
                mainSuggestedRecords: 1,
            },
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.env.models['mail.composer'].get(this.props.composerLocalId);
    }

}

Object.assign(ComposerSuggestionList, {
    components,
    defaultProps: {
        isBelow: false,
    },
    props: {
        composerLocalId: String,
        isBelow: Boolean,
    },
    template: 'mail.ComposerSuggestionList',
});

export default ComposerSuggestionList;
