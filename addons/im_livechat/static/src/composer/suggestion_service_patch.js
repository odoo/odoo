/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SuggestionService } from "@mail/composer/suggestion_service";
import { cleanTerm } from "@mail/utils/format";
import { _t } from "@web/core/l10n/translation";

patch(SuggestionService.prototype, "im_livechat", {
    getSupportedDelimiters(thread) {
        return (thread.type === "chat" && thread.correspondent?.eq(this.store.odoobot)) ||
            thread.model !== "discuss.channel" ||
            thread.type === "livechat"
            ? [...this._super(...arguments), [":"]]
            : this._super(...arguments);
    },
    /**
     * Returns suggestions that match the given search term from specified type.
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
        if (delimiter === ":") {
            return this.searchCannedResponseSuggestions(cleanTerm(term), sort);
        }
        return this._super(...arguments);
    },

    searchCannedResponseSuggestions(cleanedSearchTerm, sort) {
        const cannedResponses = this.store.cannedResponses
            .filter((cannedResponse) => {
                return cleanTerm(cannedResponse.name).includes(cleanedSearchTerm);
            })
            .map(({ id, name, substitution }) => {
                return {
                    id,
                    name,
                    substitution: _t(substitution),
                };
            });
        const sortFunc = (c1, c2) => {
            const cleanedName1 = cleanTerm(c1.name ?? "");
            const cleanedName2 = cleanTerm(c2.name ?? "");
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
