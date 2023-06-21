/* @odoo-module */

import { insertChannelMember } from "@mail/core/common/channel_member_service";
import { getRecentChatPartnerIds, insertPersona } from "@mail/core/common/persona_service";
import { insertThread } from "@mail/core/common/thread_service";
import { cleanTerm } from "@mail/utils/common/format";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { registry } from "@web/core/registry";

let orm;
/** @type {import("@mail/core/common/store_service").Store} */
let store;

export async function fetchSuggestions({ delimiter, term }, { thread, onFetched } = {}) {
    const cleanedSearchTerm = cleanTerm(term);
    switch (delimiter) {
        case "@": {
            _fetchPartners(cleanedSearchTerm, thread).then(onFetched);
            break;
        }
        case "#":
            _fetchThreads(cleanedSearchTerm).then(onFetched);
            break;
    }
}

export const getSupportedSuggestionDelimiters = makeFnPatchable(function (thread) {
    return [["@"], ["#"]];
});

function searchChannelSuggestions(cleanedSearchTerm, thread, sort) {
    let threads;
    if (
        thread &&
        (thread.type === "group" ||
            thread.type === "chat" ||
            (thread.type === "channel" && thread.authorizedGroupFullName))
    ) {
        // Only return the current channel when in the context of a
        // group restricted channel or group or chat. Indeed, the message with the mention
        // would appear in the target channel, so this prevents from
        // inadvertently leaking the private message into the mentioned
        // channel.
        threads = [thread];
    } else {
        threads = Object.values(store.threads);
    }
    const suggestionList = threads.filter(
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
        const cleanedDisplayName1 = cleanTerm(c1.displayName ?? "");
        const cleanedDisplayName2 = cleanTerm(c2.displayName ?? "");
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
    };
}

function searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
    let partners;
    const isNonPublicChannel =
        thread &&
        (thread.type === "group" ||
            thread.type === "chat" ||
            (thread.type === "channel" && thread.group_based_subscription));
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
        partners = Object.values(store.personas).filter((persona) => persona.type === "partner");
    }
    const mainSuggestionList = [];
    const extraSuggestionList = [];
    for (const partner of partners) {
        if (partner === store.odoobot) {
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
            ? sortPartnerSuggestions(mainSuggestionList, cleanedSearchTerm, thread)
            : mainSuggestionList,
        extraSuggestions: sort
            ? sortPartnerSuggestions(extraSuggestionList, cleanedSearchTerm, thread)
            : extraSuggestionList,
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
 * @returns {[mainSuggestion[], extraSuggestion[]]}
 */
export const searchSuggestions = makeFnPatchable(function (
    { delimiter, term },
    { thread } = {},
    sort = false
) {
    const cleanedSearchTerm = cleanTerm(term);
    switch (delimiter) {
        case "@": {
            return searchPartnerSuggestions(cleanedSearchTerm, thread, sort);
        }
        case "#":
            return searchChannelSuggestions(cleanedSearchTerm, thread, sort);
    }
    return {
        type: undefined,
        mainSuggestions: [],
        extraSuggestions: [],
    };
});

/**
 * @param {[import("@mail/core/common/persona_model").Persona]} [partners]
 * @param {String} [searchTerm]
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @returns {[import("@mail/core/common/persona_model").Persona]}
 */
export function sortPartnerSuggestions(partners, searchTerm = "", thread = undefined) {
    const cleanedSearchTerm = cleanTerm(searchTerm);
    /**
     * Ordering:
     * - recent chat partners
     * - internal users
     * - channel members
     * - thread followers
     * - longgest match of name, alphabetically if having same length of match
     * - longgest match of email, alphabetically if having same length of match
     * - id
     */
    return partners.sort((p1, p2) => {
        const recentChatPartnerIds = getRecentChatPartnerIds();
        const recentChatIndex_p1 = recentChatPartnerIds.findIndex(
            (partnerId) => partnerId === p1.id
        );
        const recentChatIndex_p2 = recentChatPartnerIds.findIndex(
            (partnerId) => partnerId === p2.id
        );
        if (recentChatIndex_p1 !== -1 && recentChatIndex_p2 === -1) {
            return -1;
        } else if (recentChatIndex_p1 === -1 && recentChatIndex_p2 !== -1) {
            return 1;
        } else if (recentChatIndex_p1 < recentChatIndex_p2) {
            return -1;
        } else if (recentChatIndex_p1 > recentChatIndex_p2) {
            return 1;
        }
        const isAInternalUser = p1.user?.isInternalUser;
        const isBInternalUser = p2.user?.isInternalUser;
        if (isAInternalUser && !isBInternalUser) {
            return -1;
        }
        if (!isAInternalUser && isBInternalUser) {
            return 1;
        }
        if (thread?.model === "discuss.channel") {
            const isMember1 = thread.channelMembers.some((member) => member.persona === p1);
            const isMember2 = thread.channelMembers.some((member) => member.persona === p2);
            if (isMember1 && !isMember2) {
                return -1;
            }
            if (!isMember1 && isMember2) {
                return 1;
            }
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
    });
}

/**
 * @param {string} term
 * @param {import("@mail/core/common/thread_model").Thread} thread
 */
async function _fetchPartners(term, thread) {
    const kwargs = { search: term };
    if (thread.model === "discuss.channel") {
        kwargs.channel_id = thread.id;
    }
    const suggestedPartners = await orm.call(
        "res.partner",
        thread.model === "discuss.channel"
            ? "get_mention_suggestions_from_channel"
            : "get_mention_suggestions",
        [],
        kwargs
    );
    suggestedPartners.map((data) => {
        insertPersona({ ...data, type: "partner" });
        if (data.persona?.channelMembers) {
            insertChannelMember(...data.persona.channelMembers);
        }
    });
}

async function _fetchThreads(term) {
    const suggestedThreads = await orm.call("discuss.channel", "get_mention_suggestions", [], {
        search: term,
    });
    suggestedThreads.map((data) => {
        insertThread({
            model: "discuss.channel",
            ...data,
        });
    });
}

export class SuggestionService {
    constructor(env, services) {
        orm = services.orm;
        store = services["mail.store"];
    }
}

export const suggestionService = {
    dependencies: ["orm", "mail.store", "mail.persona", "discuss.channel.member"],
    start(env, services) {
        return new SuggestionService(env, services);
    },
};

registry.category("services").add("mail.suggestion", suggestionService);
