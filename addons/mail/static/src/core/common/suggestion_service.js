import { partnerCompareRegistry } from "@mail/core/common/partner_compare";
import { cleanTerm } from "@mail/utils/common/format";
import { toRaw } from "@odoo/owl";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";

export class SuggestionService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.store = services["mail.store"];
        this.emojis;
    }

    /**
     * Returns list of supported delimiters, each supported
     * delimiter is in an array [a, b, c] where:
     * - a: chars to trigger
     * - b: (optional) if set, the exact position in composer text input to allow using this delimiter
     * - c: (optional) if set, this is the minimum amount of extra char after delimiter to allow using this delimiter
     *
     * @param {import('models').Thread} thread
     * @returns {Array<[string, number, number]>}
     */
    getSupportedDelimiters(thread) {
        return [["@"], ["#"], ["::"], [":", undefined, 2]];
    }

    async fetchSuggestions({ delimiter, term }, { thread, abortSignal } = {}) {
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@": {
                await this.fetchPartners(cleanedSearchTerm, thread, { abortSignal });
                break;
            }
            case "#":
                await this.fetchThreads(cleanedSearchTerm, { abortSignal });
                break;
            case "::":
                await this.store.cannedReponses.fetch();
                break;
            case ":": {
                const { emojis } = await loadEmoji();
                this.emojis = emojis;
                break;
            }
        }
    }

    /**
     * Make an ORM call with a cancellable signal. Usefull to abort fetch
     * requests from outside of the suggestion service.
     *
     * @param {String} model
     * @param {String} method
     * @param {Array} args
     * @param {Object} kwargs
     * @param {Object} options
     * @param {AbortSignal} options.abortSignal
     */
    makeOrmCall(model, method, args, kwargs, { abortSignal } = {}) {
        return new Promise((res, rej) => {
            const req = this.orm.silent.call(model, method, args, kwargs);
            const onAbort = () => {
                try {
                    req.abort();
                } catch (e) {
                    rej(e);
                }
            };
            abortSignal?.addEventListener("abort", onAbort);
            req.then(res)
                .catch(rej)
                .finally(() => abortSignal?.removeEventListener("abort", onAbort));
        });
    }
    /**
     * @param {string} term
     * @param {import("models").Thread} [thread]
     */
    async fetchPartners(term, thread, { abortSignal } = {}) {
        const kwargs = { search: term };
        if (thread?.model === "discuss.channel") {
            kwargs.channel_id = thread.id;
        }
        const data = await this.makeOrmCall(
            "res.partner",
            thread?.model === "discuss.channel"
                ? "get_mention_suggestions_from_channel"
                : "get_mention_suggestions",
            [],
            kwargs,
            { abortSignal }
        );
        this.store.insert(data);
    }

    /**
     * @param {string} term
     */
    async fetchThreads(term, { abortSignal } = {}) {
        const suggestedThreads = await this.makeOrmCall(
            "discuss.channel",
            "get_mention_suggestions",
            [],
            { search: term },
            { abortSignal }
        );
        this.store.Thread.insert(suggestedThreads);
    }

    searchCannedResponseSuggestions(cleanedSearchTerm, sort) {
        const cannedResponses = Object.values(this.store["mail.canned.response"].records).filter(
            (cannedResponse) => cleanTerm(cannedResponse.source).includes(cleanedSearchTerm)
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
            type: "mail.canned.response",
            suggestions: sort ? cannedResponses.sort(sortFunc) : cannedResponses,
        };
    }

    searchEmojisSuggestions(cleanedSearchTerm) {
        let emojis = [];
        if (this.emojis && cleanedSearchTerm) {
            emojis = fuzzyLookup(cleanedSearchTerm, this.emojis, (emoji) => emoji.shortcodes);
        }
        return {
            type: "emoji",
            suggestions: emojis,
        };
    }

    /**
     * Returns suggestions that match the given search term from specified type.
     *
     * @param {Object} [param0={}]
     * @param {String} [param0.delimiter] can be one one of the following: ["@", "#"]
     * @param {String} [param0.term]
     * @param {Object} [options={}]
     * @param {Integer} [options.thread] prioritize and/or restrict
     *  result in the context of given thread
     * @returns {{ type: String, suggestions: Array }}
     */
    searchSuggestions({ delimiter, term }, { thread, sort = false } = {}) {
        thread = toRaw(thread);
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@": {
                return this.searchPartnerSuggestions(cleanedSearchTerm, thread, sort);
            }
            case "#":
                return this.searchChannelSuggestions(cleanedSearchTerm, sort);
            case "::":
                return this.searchCannedResponseSuggestions(cleanedSearchTerm, sort);
            case ":":
                return this.searchEmojisSuggestions(cleanedSearchTerm);
        }
        return {
            type: undefined,
            suggestions: [],
        };
    }

    isSuggestionValid(persona, thread) {
        return persona.type === "partner" && !persona.eq(this.store.odoobot);
    }

    getPartnerSuggestions(thread) {
        return Object.values(this.store.Persona.records).filter((persona) =>
            this.isSuggestionValid(persona, thread)
        );
    }

    searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
        const partners = this.getPartnerSuggestions(thread);
        const suggestions = [];
        for (const partner of partners) {
            if (!partner.name) {
                continue;
            }
            if (
                cleanTerm(partner.name).includes(cleanedSearchTerm) ||
                (partner.email && cleanTerm(partner.email).includes(cleanedSearchTerm))
            ) {
                suggestions.push(partner);
            }
        }
        suggestions.push(
            ...this.store.specialMentions.filter(
                (special) =>
                    thread &&
                    special.channel_types.includes(thread.channel_type) &&
                    cleanedSearchTerm.length >= Math.min(4, special.label.length) &&
                    (special.label.startsWith(cleanedSearchTerm) ||
                        cleanTerm(special.description.toString()).includes(cleanedSearchTerm))
            )
        );
        return {
            type: "Partner",
            suggestions: sort
                ? [...this.sortPartnerSuggestions(suggestions, cleanedSearchTerm, thread)]
                : suggestions,
        };
    }

    /**
     * @param {[import("models").Persona | import("@mail/core/common/store_service").SpecialMention]} [partners]
     * @param {String} [searchTerm]
     * @param {import("models").Thread} thread
     * @returns {[import("models").Persona]}
     */
    sortPartnerSuggestions(partners, searchTerm = "", thread = undefined) {
        const cleanedSearchTerm = cleanTerm(searchTerm);
        const compareFunctions = partnerCompareRegistry.getAll();
        const context = this.sortPartnerSuggestionsContext(thread);
        return partners.sort((p1, p2) => {
            p1 = toRaw(p1);
            p2 = toRaw(p2);
            if (p1.isSpecial || p2.isSpecial) {
                return 0;
            }
            for (const fn of compareFunctions) {
                const result = fn(p1, p2, {
                    env: this.env,
                    searchTerm: cleanedSearchTerm,
                    thread,
                    context,
                });
                if (result !== undefined) {
                    return result;
                }
            }
        });
    }

    sortPartnerSuggestionsContext() {
        return {};
    }

    searchChannelSuggestions(cleanedSearchTerm, sort) {
        const suggestionList = Object.values(this.store.Thread.records).filter(
            (thread) =>
                thread.channel_type === "channel" &&
                thread.displayName &&
                cleanTerm(thread.displayName).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const isPublicChannel1 = c1.channel_type === "channel" && !c2.authorizedGroupFullName;
            const isPublicChannel2 = c2.channel_type === "channel" && !c2.authorizedGroupFullName;
            if (isPublicChannel1 && !isPublicChannel2) {
                return -1;
            }
            if (!isPublicChannel1 && isPublicChannel2) {
                return 1;
            }
            if (c1.hasSelfAsMember && !c2.hasSelfAsMember) {
                return -1;
            }
            if (!c1.hasSelfAsMember && c2.hasSelfAsMember) {
                return 1;
            }
            const cleanedDisplayName1 = cleanTerm(c1.displayName);
            const cleanedDisplayName2 = cleanTerm(c2.displayName);
            if (
                cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                !cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedDisplayName1 < cleanedDisplayName2) {
                return -1;
            }
            if (cleanedDisplayName1 > cleanedDisplayName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "Thread",
            suggestions: sort ? suggestionList.sort(sortFunc) : suggestionList,
        };
    }
}

export const suggestionService = {
    dependencies: ["orm", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return new SuggestionService(env, services);
    },
};

registry.category("services").add("mail.suggestion", suggestionService);
