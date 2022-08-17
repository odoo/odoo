/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

registerModel({
    name: 'CannedResponse',
    modelMethods: {
        /**
         * Fetches canned responses matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * In practice all canned responses are already fetched at init so this
         * method does nothing.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        fetchSuggestions(searchTerm, { thread } = {}) {},
        /**
         * Returns a sort function to determine the order of display of canned
         * responses in the suggestion list.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        getSuggestionSortFunction(searchTerm, { thread } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const cleanedAName = cleanSearchTerm(a.source || '');
                const cleanedBName = cleanSearchTerm(b.source || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                return a.id - b.id;
            };
        },
        /*
         * Returns canned responses that match the given search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[CannedResponse[], CannedResponse[]]}
         */
        searchSuggestions(searchTerm, { thread } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [this.messaging.cannedResponses.filter(cannedResponse =>
                cleanSearchTerm(cannedResponse.source).includes(cleanedSearchTerm)
            )];
        },
    },
    fields: {
        id: attr({
            identifying: true,
        }),
        /**
         *  The keyword to use a specific canned response.
         */
        source: attr(),
        /**
         * The canned response itself which will replace the keyword previously
         * entered.
         */
        substitution: attr(),
        suggestable: one('ComposerSuggestable', {
            default: insertAndReplace(),
            inverse: 'cannedResponse',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
