/* @odoo-module */

import { cleanTerm } from "@mail/utils/format";
import { registry } from "@web/core/registry";

export class SuggestionService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.orm = services.orm;
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/core/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
    }

    getSupportedDelimiters(thread) {
        return [["@"], ["#"]];
    }

    async fetchSuggestions({ delimiter, term }, { thread, onFetched } = {}) {
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@": {
                this.fetchPartners(cleanedSearchTerm, thread).then(onFetched);
                break;
            }
            case "#":
                this.fetchThreads(cleanedSearchTerm).then(onFetched);
                break;
        }
    }

    /**
     * @param {string} term
     * @param {import("@mail/core/thread_model").Thread} thread to override the function in case of fetch partners in channels
     */
    async fetchPartners(term, thread) {
        const kwargs = { search: term };
        const suggestedPartners = await this.orm.call(
            "res.partner",
            "get_mention_suggestions",
            [],
            kwargs
        );
        suggestedPartners.map((data) => {
            this.personaService.insert({ ...data, type: "partner" });
        });
    }

    async fetchThreads(term) {
        const suggestedThreads = await this.orm.call(
            "discuss.channel",
            "get_mention_suggestions",
            [],
            { search: term }
        );
        suggestedThreads.map((data) => {
            this.threadService.insert({
                model: "discuss.channel",
                ...data,
            });
        });
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
     * @returns {[mainSuggestion[], extraSuggestion[]]}
     */
    searchSuggestions({ delimiter, term }, { thread } = {}, sort = false) {
        if (delimiter === "@") {
            return this.searchPartnerSuggestions(cleanTerm(term), thread, sort);
        }
        return {
            type: undefined,
            mainSuggestions: [],
            extraSuggestions: [],
        };
    }

    searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
        const partners = this.partnersToSearch();
        const mainSuggestionList = [];
        const extraSuggestionList = [];
        for (const partner of partners) {
            if (partner === this.store.odoobot) {
                // ignore archived partners (except OdooBot)
                continue;
            }
            if (!partner.name) {
                continue;
            }
            if (
                cleanTerm(partner.name).includes(cleanedSearchTerm) ||
                (partner.email && cleanTerm(partner.email).includes(cleanedSearchTerm))
            ) {
                if (partner.user) {
                    mainSuggestionList.push(partner);
                } else {
                    extraSuggestionList.push(partner);
                }
            }
        }
        return {
            type: "Partner",
            mainSuggestions: sort
                ? mainSuggestionList.sort((p1, p2) =>
                      this.compareSuggestions(p1, p2, thread, cleanedSearchTerm)
                  )
                : mainSuggestionList,
            extraSuggestions: sort
                ? extraSuggestionList.sort((p1, p2) =>
                      this.compareSuggestions(p1, p2, thread, cleanedSearchTerm)
                  )
                : extraSuggestionList,
        };
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} thread to override the function in case of fetch partners in channels
     */
    partnersToSearch(thread) {
        return Object.values(this.store.personas).filter((persona) => persona.type === "partner");
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {import('@mail/core/persona_model').Persona} p1
     * @param {import('@mail/core/persona_model').Persona} p2
     * @param {string} cleanedSearchTerm
     */
    compareSuggestions(p1, p2, thread, cleanedSearchTerm) {
        const isAInternalUser = p1.user?.isInternalUser;
        const isBInternalUser = p2.user?.isInternalUser;
        if (isAInternalUser && !isBInternalUser) {
            return -1;
        }
        if (!isAInternalUser && isBInternalUser) {
            return 1;
        }
        if (thread) {
            const isFollower1 = thread.followers.some((follower) => follower.partner === p1);
            const isFollower2 = thread.followers.some((follower) => follower.partner === p2);
            if (isFollower1 && !isFollower2) {
                return -1;
            }
            if (!isFollower1 && isFollower2) {
                return 1;
            }
        }
        const cleanedName1 = cleanTerm(p1.name ?? "");
        const cleanedName2 = cleanTerm(p2.name ?? "");
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
        const cleanedEmail1 = cleanTerm(p1.email ?? "");
        const cleanedEmail2 = cleanTerm(p2.email ?? "");
        if (
            cleanedEmail1.startsWith(cleanedSearchTerm) &&
            !cleanedEmail1.startsWith(cleanedSearchTerm)
        ) {
            return -1;
        }
        if (
            !cleanedEmail2.startsWith(cleanedSearchTerm) &&
            cleanedEmail2.startsWith(cleanedSearchTerm)
        ) {
            return 1;
        }
        if (cleanedEmail1 < cleanedEmail2) {
            return -1;
        }
        if (cleanedEmail1 > cleanedEmail2) {
            return 1;
        }
        return p1.id - p2.id;
    }
}

export const suggestionService = {
    dependencies: ["orm", "mail.store", "mail.thread", "mail.persona", "discuss.channel.member"],
    start(env, services) {
        return new SuggestionService(env, services);
    },
};

registry.category("services").add("mail.suggestion", suggestionService);
