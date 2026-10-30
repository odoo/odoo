import { Plugin } from "@html_editor/plugin";

import { compareDatetime } from "@mail/utils/common/misc";

import { localeCompare, normalize } from "@web/core/l10n/utils";

/** Suggests the canned responses to insert after `::`. */
export class CannedResponseSuggestionPlugin extends Plugin {
    static id = "cannedResponseSuggestion";
    /** @type {import("plugins").EditorResources} */
    resources = {
        suggestion_sources: {
            delimiter: "::",
            // guests have no canned responses
            fetch: () =>
                this.services["mail.store"].self_user &&
                this.services["mail.store"].cannedReponses.fetch(),
            search: (cleanedTerm) => this.search(cleanedTerm),
            toOptions: (cannedResponses) => ({
                optionTemplate: "mail.Composer.suggestionCannedResponse",
                options: cannedResponses.map((cannedResponse) => ({
                    cannedResponse,
                    label: cannedResponse.substitution,
                    source: cannedResponse.source,
                    title: cannedResponse.substitution,
                })),
            }),
        },
    };

    /** @param {string} cleanedTerm */
    search(cleanedTerm) {
        const cannedResponses = [
            ...this.services["mail.store"]["mail.canned.response"].records.values(),
        ].filter((cannedResponse) => normalize(cannedResponse.source).includes(cleanedTerm));
        const sortFunc = (c1, c2) => {
            const cleanedName1 = normalize(c1.source);
            const cleanedName2 = normalize(c2.source);
            if (cleanedName1.startsWith(cleanedTerm) && !cleanedName2.startsWith(cleanedTerm)) {
                return -1;
            }
            if (!cleanedName1.startsWith(cleanedTerm) && cleanedName2.startsWith(cleanedTerm)) {
                return 1;
            }
            return (
                compareDatetime(c2.last_used, c1.last_used) ||
                localeCompare(c1.source, c2.source) ||
                c1.id - c2.id
            );
        };
        return cannedResponses.sort(sortFunc);
    }
}
