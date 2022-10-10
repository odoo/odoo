/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputSuggestionListView',
    recordMethods:{
        /**
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        setFirstSuggestionViewActive() {
            const firstSuggestionView = this.suggestionViews[0];
            this.update({ rawActiveSuggestionView: firstSuggestionView });
        },
        setLastSuggestionViewActive() {
            const { length, [length - 1]: lastSuggestionView } = this.suggestionViews;
            this.update({ rawActiveSuggestionView: lastSuggestionView });
        },
        setNextSuggestionViewActive() {
            const activeElementIndex = this.suggestionViews.findIndex(
                suggestion => suggestion === this.activeSuggestionView
            );
            if (activeElementIndex === this.suggestionViews.length - 1) {
                // loop when reaching the end of the list
                this.setFirstSuggestionViewActive();
                return;
            }
            const nextSuggestionView = this.suggestionViews[activeElementIndex + 1];
            this.update({ rawActiveSuggestionView: nextSuggestionView });
        },
        setPreviousSuggestionViewActive() {
            const activeElementIndex = this.suggestionViews.findIndex(
                suggestion => suggestion === this.activeSuggestionView
            );
            if (activeElementIndex === 0) {
                // loop when reaching the start of the list
                this.setLastSuggestionViewActive();
                return;
            }
            const previousSuggestionView = this.suggestionViews[activeElementIndex - 1];
            this.update({ rawActiveSuggestionView: previousSuggestionView });
        },
    },
    fields: {
        /**
         * Determines the suggestion that is currently active. This suggestion
         * is highlighted in the UI and it will be selected when the
         * suggestion is confirmed by the user.
         */
        activeSuggestionView: one('AutocompleteInputSuggestionView', {
            compute() {
                if (this.suggestionViews.includes(this.rawActiveSuggestionView)) {
                    return this.rawActiveSuggestionView;
                }
                const firstSuggestionView = this.suggestionViews[0];
                return firstSuggestionView;
            },
        }),
        component: attr(),
        owner: one('AutocompleteInputView', {
            identifying: true,
            inverse: 'autocompleteInputSuggestionListView',
        }),
        rawActiveSuggestionView: one('AutocompleteInputSuggestionView'),
        suggestionViews: many('AutocompleteInputSuggestionView', {
            compute() {
                if(this.owner.suggestions.length > 0) {
                    const suggestionViewsList = [];
                    for(const suggestion of this.owner.suggestions) {
                        suggestionViewsList.push({
                            autocompleteInputSuggestable: suggestion,
                        })
                    }
                    return suggestionViewsList;
                }
                return clear();
            },
            inverse: 'autocompleteInputSuggestionListView',
        })
    },
});
