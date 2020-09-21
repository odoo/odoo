odoo.define('mail/static/src/components/composer_suggestion_list/composer_suggestion_list.js', function (require) {
'use strict';

const components = {
    ComposerSuggestion: require('mail/static/src/components/composer_suggestion/composer_suggestion.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ComposerSuggestionList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(props.composerLocalId);
            const activeSuggestedRecord = composer
                ? composer.activeSuggestedRecord
                : undefined;
            const extraSuggestedRecordsList = composer
                ? composer.extraSuggestedRecordsList
                : [];
            const mainSuggestedRecordsList = composer
                ? composer.mainSuggestedRecordsList
                : [];
            return {
                activeSuggestedRecord: activeSuggestedRecord ? activeSuggestedRecord.__state : undefined,
                composer: composer ? composer.__state : undefined,
                extraSuggestedRecordsList: extraSuggestedRecordsList
                    ? extraSuggestedRecordsList.map(record => record.__state)
                    : [],
                mainSuggestedRecordsList: mainSuggestedRecordsList
                    ? mainSuggestedRecordsList.map(record => record.__state)
                    : [],
            };
        }, {
            compareDepth: {
                extraSuggestedRecordsList: 1,
                mainSuggestedRecordsList: 1,
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
