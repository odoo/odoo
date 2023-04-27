odoo.define('mail/static/src/components/composer_suggestion_list/composer_suggestion_list.js', function (require) {
'use strict';

const components = {
    ComposerSuggestion: require('mail/static/src/components/composer_suggestion/composer_suggestion.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

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

return ComposerSuggestionList;

});
