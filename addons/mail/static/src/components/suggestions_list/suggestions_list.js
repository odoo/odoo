odoo.define('mail/static/src/components/suggestions_list/suggestions_list.js', function (require) {
'use strict';

const components = {
    Suggestion: require('mail/static/src/components/suggestion/suggestion.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class SuggestionsList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const suggestionManager = this.env.models['mail.suggestionManager'].get(props.suggestionManagerLocalId);
            const activeSuggestedRecord = suggestionManager
                ? suggestionManager.activeSuggestedRecord
                : undefined;
            const extraSuggestedRecords = suggestionManager
                ? suggestionManager.extraSuggestedRecords
                : [];
            const mainSuggestedRecords = suggestionManager
                ? suggestionManager.mainSuggestedRecords
                : [];
            return {
                activeSuggestedRecord,
                suggestionManager,
                suggestionManagerSuggestionModelName: suggestionManager && suggestionManager.suggestionModelName,
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
     * @returns {mail.suggestion}
     */
    get suggestionManager() {
        return this.env.models['mail.suggestionManager'].get(this.props.suggestionManagerLocalId);
    }

    /**
     * Key events management is performed in a Keyup to avoid intempestive RPC calls
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        switch (ev.key) {
            case 'Escape':
                // already handled in _onKeydownTextarea, break to avoid default
                break;
            // ENTER, HOME, END, UP, DOWN, PAGE UP, PAGE DOWN, TAB: check if navigation in mention suggestions
            case 'Enter':
                if (this.suggestionManager.hasSuggestions) {
                    this.trigger('suggestion-selected', true);
                    this.suggestionManager.closeSuggestions();
                }
                break;
            case 'ArrowUp':
            case 'PageUp':
                if (this.suggestionManager.hasSuggestions) {
                    this.suggestionManager.setPreviousSuggestionActive();
                    this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'ArrowDown':
            case 'PageDown':
                if (this.suggestionManager.hasSuggestions) {
                    this.suggestionManager.setNextSuggestionActive();
                    this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'Home':
                if (this.suggestionManager.hasSuggestions) {
                    this.suggestionManager.setFirstSuggestionActive();
                    this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'End':
                if (this.suggestionManager.hasSuggestions) {
                    this.suggestionManager.setLastSuggestionActive();
                    this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'Tab':
                if (this.suggestionManager.hasSuggestions) {
                    if (ev.shiftKey) {
                        this.suggestionManager.setPreviousSuggestionActive();
                        this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                    } else {
                        this.suggestionManager.setNextSuggestionActive();
                        this.suggestionManager.update({ hasToScrollToActiveSuggestion: true });
                    }
                }
                break;
            case 'Alt':
            case 'AltGraph':
            case 'CapsLock':
            case 'Control':
            case 'Fn':
            case 'FnLock':
            case 'Hyper':
            case 'Meta':
            case 'NumLock':
            case 'ScrollLock':
            case 'Shift':
            case 'ShiftSuper':
            case 'Symbol':
            case 'SymbolLock':
                // prevent modifier keys from resetting the suggestion state
                break;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

}

Object.assign(SuggestionsList, {
    components,
    props: {
        suggestionManagerLocalId: String,
        isBelow: Boolean,
    },
    template: 'mail.SuggestionsList',
});

return SuggestionsList;

});
