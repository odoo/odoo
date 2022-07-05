/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ComposerSuggestionListView',
    identifyingFields: ['composerViewOwner'],
    recordMethods: {
        /**
         * Adapts the active suggestion it if the active suggestion is no longer
         * part of the suggestions.
         *
         * @private
         * @returns {FieldCommand}
         */
        _computeActiveSuggestionView() {
            if (
                this.mainSuggestionViews.includes(this.activeSuggestionView) ||
                this.extraSuggestionViews.includes(this.activeSuggestionView)
            ) {
                return;
            }
            const suggestionViews = this.mainSuggestionViews.concat(this.extraSuggestionViews);
            const firstSuggestionView = suggestionViews[0];
            return replace(firstSuggestionView);
        },
        /**
         * @returns {FieldCommand}
         */
        _computeExtraSuggestionViews() {
            return insertAndReplace(this.composerViewOwner.extraSuggestions.map(suggestable => {
                return {
                    suggestable: replace(suggestable),
                };
            }));
        },
        /**
         * @returns {FieldCommand}
         */
        _computeMainSuggestionViews() {
            return insertAndReplace(this.composerViewOwner.mainSuggestions.map(suggestable => {
                return {
                    suggestable: replace(suggestable),
                };
            }));
        },
    },
    fields: {
        /**
         * Determines the suggestion that is currently active. This suggestion
         * is highlighted in the UI and it will be selected when the
         * suggestion is confirmed by the user.
         */
        activeSuggestionView: one('ComposerSuggestionView', {
            compute: '_computeActiveSuggestionView',
            inverse: 'composerSuggestionListViewOwnerAsActiveSuggestionView',
        }),
        composerViewOwner: one('ComposerView', {
            inverse: 'composerSuggestionListView',
            readonly: true,
            required: true,
        }),
        extraSuggestionViews: many('ComposerSuggestionView', {
            compute: '_computeExtraSuggestionViews',
            inverse: 'composerSuggestionListViewOwnerAsExtraSuggestion',
            isCausal: true,
        }),
        /**
         * Determines whether the currently active suggestion should be scrolled
         * into view.
         */
        hasToScrollToActiveSuggestionView: attr({
            default: false,
        }),
        mainSuggestionViews: many('ComposerSuggestionView', {
            compute: '_computeMainSuggestionViews',
            inverse: 'composerSuggestionListViewOwnerAsMainSuggestion',
            isCausal: true,
        }),
    },
});
