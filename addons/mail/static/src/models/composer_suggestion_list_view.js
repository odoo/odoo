/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ComposerSuggestionListView',
    identifyingFields: ['composerViewOwner'],
    recordMethods: {
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
        mainSuggestionViews: many('ComposerSuggestionView', {
            compute: '_computeMainSuggestionViews',
            inverse: 'composerSuggestionListViewOwnerAsMainSuggestion',
            isCausal: true,
        }),
    },
});
