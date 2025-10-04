/* @odoo-module */

import { partnerCompareRegistry } from "@mail/core/common/partner_compare";
import { cleanTerm } from "@mail/utils/common/format";
import { toRaw } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class SuggestionService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.store = services["mail.store"];
        this.personaService = services["mail.persona"];
    }

    getSupportedDelimiters(thread) {
        return [["@"], ["#"]];
    }

    async fetchSuggestions({ delimiter, term }, { thread } = {}) {
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@": {
                await this.fetchPartners(cleanedSearchTerm, thread);
                break;
            }
            case "#":
                await this.fetchThreads(cleanedSearchTerm);
                break;
        }
    }

    /**
     * @param {string} term
     * @param {import("models").Thread} [thread]
     */
    async fetchPartners(term, thread) {
        const kwargs = { search: term };
        if (thread?.model === "discuss.channel") {
            kwargs.channel_id = thread.id;
        }
        const suggestedPartners = await this.orm.silent.call(
            "res.partner",
            thread?.model === "discuss.channel"
                ? "get_mention_suggestions_from_channel"
                : "get_mention_suggestions",
            [],
            kwargs
        );
        this.store.Persona.insert(suggestedPartners);
    }

    /**
     * @param {string} term
     */
    async fetchThreads(term) {
        const suggestedThreads = await this.orm.silent.call(
            "discuss.channel",
            "get_mention_suggestions",
            [],
            { search: term }
        );
        this.store.Thread.insert(suggestedThreads);
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
     * @returns {{ type: String, mainSuggestions: Array, extraSuggestions: Array }}
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
        }
        return {
            type: undefined,
            mainSuggestions: [],
            extraSuggestions: [],
        };
    }

    searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
        let partners;
        const isNonPublicChannel =
            thread &&
            (thread.type === "group" ||
                thread.type === "chat" ||
                (thread.type === "channel" && thread.authorizedGroupFullName));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            partners = thread.channelMembers
                .map((member) => member.persona)
                .filter((persona) => persona.type === "partner");
        } else {
            partners = Object.values(this.store.Persona.records).filter(
                (persona) => persona.type === "partner"
            );
        }
        const mainSuggestionList = [];
        const extraSuggestionList = [];
        for (const partner of partners) {
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
                ? this.sortPartnerSuggestions(mainSuggestionList, cleanedSearchTerm, thread)
                : mainSuggestionList,
            extraSuggestions: sort
                ? this.sortPartnerSuggestions(extraSuggestionList, cleanedSearchTerm, thread)
                : extraSuggestionList,
        };
    }

    /**
     * @param {[import("models").Persona]} [partners]
     * @param {String} [searchTerm]
     * @param {import("models").Thread} thread
     * @returns {[import("models").Persona]}
     */
    sortPartnerSuggestions(partners, searchTerm = "", thread = undefined) {
        const cleanedSearchTerm = cleanTerm(searchTerm);
        const compareFunctions = partnerCompareRegistry.getAll();
        const context = { recentChatPartnerIds: this.personaService.getRecentChatPartnerIds() };
        const memberPartnerIds = new Set(
            thread?.channelMembers
                .filter((member) => member.persona.type === "partner")
                .map((member) => member.persona.id)
        );
        return partners.sort((p1, p2) => {
            p1 = toRaw(p1);
            p2 = toRaw(p2);
            for (const fn of compareFunctions) {
                const result = fn(p1, p2, {
                    env: this.env,
                    memberPartnerIds,
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

    searchChannelSuggestions(cleanedSearchTerm, sort) {
        const suggestionList = Object.values(this.store.Thread.records).filter(
            (thread) =>
                thread.type === "channel" &&
                thread.displayName &&
                cleanTerm(thread.displayName).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const isPublicChannel1 = c1.type === "channel" && !c2.authorizedGroupFullName;
            const isPublicChannel2 = c2.type === "channel" && !c2.authorizedGroupFullName;
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
            mainSuggestions: sort ? suggestionList.sort(sortFunc) : suggestionList,
            extraSuggestions: [],
        };
    }
}

export const suggestionService = {
    dependencies: ["orm", "mail.store", "mail.persona"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new SuggestionService(env, services);
    },
};

registry.category("services").add("mail.suggestion", suggestionService);
