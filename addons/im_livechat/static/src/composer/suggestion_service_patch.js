/* @odoo-module */

import {
    SuggestionService,
    getSupportedSuggestionDelimiters,
    searchSuggestions,
} from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";
import { patchFn } from "@mail/utils/common/patch";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

let store;

patchFn(getSupportedSuggestionDelimiters, function (thread) {
    return thread?.type === "livechat"
        ? [...this._super(...arguments), [":"]]
        : this._super(...arguments);
});

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
patchFn(searchSuggestions, function ({ delimiter, term }, { thread } = {}, sort = false) {
    if (delimiter === ":") {
        return searchCannedResponseSuggestions(cleanTerm(term), sort);
    }
    return this._super(...arguments);
});

function searchCannedResponseSuggestions(cleanedSearchTerm, sort) {
    const cannedResponses = store.cannedResponses
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
}

patch(SuggestionService.prototype, "im_livechat", {
    setup(env, services) {
        this._super(...arguments);
        store = services["mail.store"];
    },
});
