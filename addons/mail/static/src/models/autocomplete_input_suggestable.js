/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputSuggestable',
    identifyingMode: 'xor',
    fields: {
        channel: one('Channel', {
            identifying: true,
            inverse: 'autocompleteInputSuggestable',
        }),
        nameToCreateChannel: attr({
            related: 'ownerAsCreatingChannel.searchTerm',
        }),
        ownerAsCreatingChannel: one('AutocompleteInputView', {
            identifying: true,
            inverse: 'creatingChannelSuggestable',
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'autocompleteInputSuggestable',
        }),
        suggestionView: one('AutocompleteInputSuggestionView', {
            inverse: 'autocompleteInputSuggestable',
        }),
    },
});
