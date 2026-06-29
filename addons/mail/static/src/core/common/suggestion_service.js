import { COMPOSER_TYPES } from "@mail/core/common/composer";
import { partnerCompareRegistry } from "@mail/core/common/partner_compare";
import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";

import { emojiLoader } from "@web/core/emoji_picker/emoji_loader";
import { localeCompare, normalize } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";

/** @typedef {import("@mail/core/common/suggestion_hook").SuggestionDelimiter} SuggestionDelimiter */

export class SuggestionService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.store = services["mail.store"];
        this.composer = services["mail.composer"];
    }

    /**
     * Returns list of supported delimiters, each supported
     * delimiter is in an array [a, b, c] where:
     * - a: chars to trigger
     * - b: (optional) if set, the exact position in composer text input to allow using this delimiter
     * - c: (optional) if set, this is the minimum amount of extra char after delimiter to allow using this delimiter
     *
     * @param {import('models').Thread} thread
     * @returns {Array<[SuggestionDelimiter, number, number]>}
     */
    getSupportedDelimiters(thread, owner) {
        const delimiters = [
            [SUGGESTION_DELIMITERS.PARTNER],
            [SUGGESTION_DELIMITERS.CANNED_RESPONSE],
        ];
        // the emoji plugin handles the emoji suggestions already
        if (!this.composer.htmlEnabled) {
            delimiters.push([SUGGESTION_DELIMITERS.EMOJI, undefined, 2]);
        }
        return delimiters;
    }

    /**
     * @param {Object} [param0={}]
     * @param {SuggestionDelimiter} [param0.delimiter]
     * @param {string} [param0.term]
     * @param {Object} [options={}]
     * @param {import("models").Thread} [options.thread]
     * @param {AbortSignal} [options.abortSignal]
     * @param {COMPOSER_TYPES} [options.composerType]
     */
    async fetchSuggestions({ delimiter, term }, { thread, abortSignal, composerType } = {}) {
        const cleanedSearchTerm = normalize(term);
        switch (delimiter) {
            case SUGGESTION_DELIMITERS.PARTNER:
                await this.fetchPartnersRoles(cleanedSearchTerm, {
                    abortSignal,
                    internalUsersOnly: composerType === COMPOSER_TYPES.NOTE,
                    thread,
                });
                break;
            case SUGGESTION_DELIMITERS.CANNED_RESPONSE:
                await this.store.cannedReponses.fetch();
                break;
            case SUGGESTION_DELIMITERS.EMOJI: {
                await emojiLoader.load();
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
     * @param {Object} [options={}]
     * @param {AbortSignal} [options.abortSignal]
     * @param {boolean} [options.internalUsersOnly]
     * @param {import("models").Thread} [options.thread]
     */
    async fetchPartnersRoles(term, { abortSignal, internalUsersOnly, thread } = {}) {
        const kwargs = { search: term };
        if (thread?.channel) {
            kwargs.channel_id = thread.id;
        } else {
            kwargs.internal_users_only = internalUsersOnly;
        }
        const data = await this.makeOrmCall(
            "res.partner",
            thread?.channel ? "get_mention_suggestions_from_channel" : "get_mention_suggestions",
            [],
            kwargs,
            { abortSignal }
        );
        this.store.insert(data);
    }

    searchCannedResponseSuggestions(cleanedSearchTerm) {
        const cannedResponses = Object.values(this.store["mail.canned.response"].records).filter(
            (cannedResponse) => normalize(cannedResponse.source).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const cleanedName1 = normalize(c1.source);
            const cleanedName2 = normalize(c2.source);
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
            return localeCompare(c1.source, c2.source) || c1.id - c2.id;
        };
        return {
            type: "mail.canned.response",
            suggestions: cannedResponses.sort(sortFunc),
        };
    }

    searchEmojisSuggestions(cleanedSearchTerm) {
        let emojis = [];
        if (emojiLoader.loaded && cleanedSearchTerm) {
            emojis = fuzzyLookup(
                cleanedSearchTerm,
                emojiLoader.emojis,
                (emoji) => emoji.shortcodes
            );
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
     * @param {SuggestionDelimiter} [param0.delimiter]
     * @param {String} [param0.term]
     * @param {Object} [options={}]
     * @param {COMPOSER_TYPES} [options.composerType]
     * @param {import("models").Thread} [options.thread] prioritize and/or restrict
     *  result in the context of given thread
     * @returns {{ type: String, suggestions: Array }}
     */
    searchSuggestions({ delimiter, term }, { composerType, thread } = {}) {
        const cleanedSearchTerm = normalize(term);
        switch (delimiter) {
            case SUGGESTION_DELIMITERS.PARTNER: {
                const partners = this.searchPartnerSuggestions(cleanedSearchTerm, {
                    composerType,
                    thread,
                });
                const roles = this.searchRoleSuggestions(cleanedSearchTerm);
                return {
                    type: "Partner",
                    suggestions: [...partners.suggestions, ...roles.suggestions],
                };
            }
            case SUGGESTION_DELIMITERS.CANNED_RESPONSE:
                return this.searchCannedResponseSuggestions(cleanedSearchTerm);
            case SUGGESTION_DELIMITERS.EMOJI:
                return this.searchEmojisSuggestions(cleanedSearchTerm);
        }
        return {
            type: undefined,
            suggestions: [],
        };
    }

    searchRoleSuggestions(cleanedSearchTerm) {
        const roles = Object.values(this.store["res.role"].records).filter((role) =>
            normalize(role.name).includes(cleanedSearchTerm)
        );
        const sortFunc = (r1, r2) => {
            const cleanedName1 = normalize(r1.name);
            const cleanedName2 = normalize(r2.name);
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
            return localeCompare(r1.name, r2.name) || r1.id - r2.id;
        };
        return {
            suggestions: roles.sort(sortFunc),
        };
    }

    /**
     * @param {import("models").Persona} [partner]
     * @param {Object} [options={}]
     * @param {COMPOSER_TYPES} [options.composerType]
     * @param {import("models").Thread} [options.thread]
     */
    isPartnerSuggestionValid(partner, { composerType, thread } = {}) {
        if (composerType === COMPOSER_TYPES.NOTE) {
            return partner.partner_share === false && partner.notEq(this.store.odoobot);
        }
        return (
            (this.store.self_user?.share === false || partner.mention_token) &&
            partner.notEq(this.store.odoobot)
        );
    }

    /**
     * @param {Object} [options={}]
     * @param {COMPOSER_TYPES} [options.composerType]
     * @param {import("models").Thread} [options.thread]
     */
    getPartnerSuggestions({ composerType, thread } = {}) {
        return Object.values(this.store["res.partner"].records).filter((partner) =>
            this.isPartnerSuggestionValid(partner, {
                composerType,
                thread,
            })
        );
    }

    /**
     * @param {string} cleanedSearchTerm
     * @param {Object} [options={}]
     * @param {COMPOSER_TYPES} [options.composerType]
     * @param {import("models").Thread} [options.thread]
     */
    searchPartnerSuggestions(cleanedSearchTerm, { composerType, thread } = {}) {
        const partners = this.getPartnerSuggestions({ composerType, thread });
        const suggestions = [];
        for (const partner of partners) {
            const name = thread?.getPersonaName(partner) ?? partner.displayName;
            if (
                (name && normalize(name).includes(cleanedSearchTerm)) ||
                (partner.email && normalize(partner.email).includes(cleanedSearchTerm))
            ) {
                suggestions.push(partner);
            }
        }
        suggestions.push(
            ...this.store.specialMentions.filter(
                (special) =>
                    thread &&
                    special.channel_types.includes(thread.channel?.channel_type) &&
                    cleanedSearchTerm.length >= Math.min(4, special.label.length) &&
                    (special.label.startsWith(cleanedSearchTerm) ||
                        normalize(special.description).includes(cleanedSearchTerm))
            )
        );
        return {
            type: "Partner",
            suggestions: [...this.sortPartnerSuggestions(suggestions, cleanedSearchTerm, thread)],
        };
    }

    /**
     * @param {[import("models").Persona | import("@mail/core/common/store_service").SpecialMention]} [partners]
     * @param {String} [searchTerm]
     * @param {import("models").Thread} thread
     * @returns {[import("models").Persona]}
     */
    sortPartnerSuggestions(partners, searchTerm = "", thread = undefined) {
        const cleanedSearchTerm = normalize(searchTerm);
        const compareFunctions = partnerCompareRegistry.getAll();
        const context = this.sortPartnerSuggestionsContext(thread);
        return partners.sort((p1, p2) => {
            if (p1.isSpecial || p2.isSpecial) {
                return 0;
            }
            for (const fn of compareFunctions) {
                const result = fn(p1, p2, {
                    store: this.store,
                    searchTerm: cleanedSearchTerm,
                    thread,
                    context,
                });
                if (result !== undefined) {
                    return result;
                }
            }
            return 0;
        });
    }

    /** @param {import("models").Thread} thread The thread from which the suggestions are triggered. */
    sortPartnerSuggestionsContext(thread) {
        const latestMessageIdByAuthorId = new Map();
        for (const { author_id, id } of thread?.messages || []) {
            if (author_id && !latestMessageIdByAuthorId.has(author_id.id)) {
                latestMessageIdByAuthorId.set(author_id.id, id);
            }
        }
        return { latestMessageIdByAuthorId };
    }
}

export const suggestionService = {
    dependencies: ["orm", "mail.store", "mail.composer"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return new SuggestionService(env, services);
    },
};

registry.category("services").add("mail.suggestion", suggestionService);
