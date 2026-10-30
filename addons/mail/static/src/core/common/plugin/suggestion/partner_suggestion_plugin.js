import { Plugin } from "@html_editor/plugin";

import {
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
} from "@mail/utils/common/format";

import { localeCompare, normalize } from "@web/core/l10n/utils";

/** Suggests the partners and roles to mention after `@`. */
export class PartnerSuggestionPlugin extends Plugin {
    static id = "partnerSuggestion";
    /** @type {import("plugins").EditorResources} */
    resources = {
        suggestion_sources: {
            delimiter: "@",
            // guests cannot access the mention suggestions
            fetch: (cleanedTerm, { abortSignal }) =>
                this.store.self_user && this.fetch(cleanedTerm, abortSignal),
            isAvailable: () => this.isAvailable(),
            search: (cleanedTerm) => this.search(cleanedTerm),
            toNode: (option) => this.toNode(option),
            toOptions: (suggestions) => this.toOptions(suggestions),
        },
    };

    /** @type {{ getThread: () => import("models").Thread|null, isNote: () => boolean }} */
    deps;
    /** @type {import("models").Store} */
    store;

    setup() {
        this.deps = this.config.composerPluginDependencies;
        this.store = this.services["mail.store"];
    }

    /**
     * @param {string} model
     * @param {string} method
     * @param {Array} args
     * @param {Object} kwargs
     * @param {AbortSignal} abortSignal
     */
    callOrm(model, method, args, kwargs, abortSignal) {
        const request = this.services.orm.silent.call(model, method, args, kwargs);
        const onAbort = () => request.abort();
        abortSignal.addEventListener("abort", onAbort);
        return request.finally(() => abortSignal.removeEventListener("abort", onAbort));
    }

    /**
     * @param {string} cleanedTerm
     * @param {AbortSignal} abortSignal
     */
    async fetch(cleanedTerm, abortSignal) {
        const thread = this.deps.getThread();
        const kwargs = { search: cleanedTerm };
        if (thread?.channel) {
            kwargs.channel_id = thread.id;
        } else {
            kwargs.internal_users_only = this.deps.isNote();
        }
        const data = await this.callOrm(
            "res.partner",
            thread?.channel ? "get_mention_suggestions_from_channel" : "get_mention_suggestions",
            [],
            kwargs,
            abortSignal
        );
        this.store.insert(data);
    }

    getPartners() {
        return [...this.store["res.partner"].records.values()].filter((partner) =>
            this.isPartnerValid(partner)
        );
    }

    isAvailable() {
        return true;
    }

    /** @param {import("models").ResPartner} partner */
    isPartnerValid(partner) {
        if (this.deps.isNote()) {
            return partner.partner_share === false && partner.notEq(this.store.odoobot);
        }
        return (
            (this.store.self_user?.share === false || partner.mention_token) &&
            partner.notEq(this.store.odoobot)
        );
    }

    /** @param {string} cleanedTerm */
    search(cleanedTerm) {
        return [...this.searchPartners(cleanedTerm), ...this.searchRoles(cleanedTerm)];
    }

    /** @param {string} cleanedTerm */
    searchPartners(cleanedTerm) {
        const thread = this.deps.getThread();
        const suggestions = [];
        for (const partner of this.getPartners()) {
            const name = thread?.getPersonaName(partner) ?? partner.displayName;
            if (
                (name && normalize(name).includes(cleanedTerm)) ||
                (partner.email && normalize(partner.email).includes(cleanedTerm))
            ) {
                suggestions.push(partner);
            }
        }
        suggestions.push(
            ...this.store.specialMentions.filter(
                (special) =>
                    thread &&
                    special.channel_types.includes(thread.channel?.channel_type) &&
                    cleanedTerm.length >= Math.min(4, special.label.length) &&
                    (special.label.startsWith(cleanedTerm) ||
                        normalize(special.description).includes(cleanedTerm))
            )
        );
        return this.store.sortPartnerSuggestions(suggestions, cleanedTerm, thread);
    }

    /** @param {string} cleanedTerm */
    searchRoles(cleanedTerm) {
        const roles = [...this.store["res.role"].records.values()].filter((role) =>
            normalize(role.name).includes(cleanedTerm)
        );
        const sortFunc = (r1, r2) => {
            const cleanedName1 = normalize(r1.name);
            const cleanedName2 = normalize(r2.name);
            if (cleanedName1.startsWith(cleanedTerm) && !cleanedName2.startsWith(cleanedTerm)) {
                return -1;
            }
            if (!cleanedName1.startsWith(cleanedTerm) && cleanedName2.startsWith(cleanedTerm)) {
                return 1;
            }
            return localeCompare(r1.name, r2.name) || r1.id - r2.id;
        };
        return roles.sort(sortFunc);
    }

    /** @param {import("@mail/core/common/navigable_list").Option} option */
    toNode(option) {
        if (option.partner) {
            return generatePartnerMentionElement(option.partner, { thread: this.deps.getThread() });
        }
        if (option.isSpecial) {
            return generateSpecialMentionElement(option.label);
        }
        return generateRoleMentionElement(option.role);
    }

    /**
     * @param {Array<import("models").ResPartner
     *   | import("models").ResRole
     *   | import("@mail/core/common/store_plugin").SpecialMention>} suggestions
     */
    toOptions(suggestions) {
        const thread = this.deps.getThread();
        return {
            optionTemplate: "mail.Composer.suggestionPartner",
            options: suggestions.map((suggestion) => {
                if (suggestion.isSpecial) {
                    return {
                        ...suggestion,
                        group: 3,
                        optionTemplate: "mail.Composer.suggestionSpecial",
                    };
                }
                if (suggestion?.Model?.getName?.() === "res.role") {
                    return {
                        group: 2,
                        label: suggestion.name,
                        role: suggestion,
                        thread,
                        optionTemplate: "mail.Composer.suggestionRole",
                    };
                }
                return {
                    group: 1,
                    label: (
                        thread?.getPersonaName(suggestion) ||
                        suggestion.displayName ||
                        suggestion.email ||
                        ""
                    ).trim(),
                    partner: suggestion,
                    thread,
                };
            }),
        };
    }
}
