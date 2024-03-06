/* @odoo-module */

import { SuggestionService } from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    getSupportedDelimiters(thread) {
        return thread?.model !== "discuss.channel" || thread.type === "livechat"
            ? [...super.getSupportedDelimiters(...arguments), [":"]]
            : super.getSupportedDelimiters(...arguments);
    },
    async fetchSuggestions({ delimiter, term }, { thread } = {}) {
        if (thread?.type === "livechat" && delimiter === "#") {
            return;
        }
        return super.fetchSuggestions(...arguments);
    },
    /**
     * Returns suggestions that match the given search term from specified type.
     * Searching on channels is disabled in livechat since the visitor don't have access to channels.
     *
     * @param {Object} [param0={}]
     * @param {String} [param0.delimiter] can be one one of the following: ["@", ":", "#", "/"]
     * @param {String} [param0.term]
     * @param {Object} [options={}]
     * @param {Integer} [options.thread] prioritize and/or restrict
     *  result in the context of given thread
     * @returns {[mainSuggestion[], extraSuggestion[]]}
     */
    searchSuggestions({ delimiter, term }, { thread } = {}, sort = false) {
        if (thread?.type === "livechat" && delimiter === "#") {
            return {
                type: undefined,
                mainSuggestions: [],
                extraSuggestions: [],
            };
        }
        if (delimiter === ":") {
            return this.searchCannedResponseSuggestions(cleanTerm(term), sort);
        }
        return super.searchSuggestions(...arguments);
    },

    searchCannedResponseSuggestions(cleanedSearchTerm, sort) {
        const cannedResponses = Object.values(this.store.CannedResponse.records).filter(
            (cannedResponse) => {
                return cleanTerm(cannedResponse.source).includes(cleanedSearchTerm);
            }
        );
        const sortFunc = (c1, c2) => {
            const cleanedName1 = cleanTerm(c1.source);
            const cleanedName2 = cleanTerm(c2.source);
            if (
                cleanedName1.startsWith(cleanedSearchTerm) &&
                !cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedName1.startsWith(cleanedSearchTerm) &&
                cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedName1 < cleanedName2) {
                return -1;
            }
            if (cleanedName1 > cleanedName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "CannedResponse",
            mainSuggestions: sort ? cannedResponses.sort(sortFunc) : cannedResponses,
        };
    },
});
