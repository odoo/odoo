import { localeCompare, normalize } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";

/**
 * Registry of functions to sort partner suggestions.
 * The expected value is a function with the following
 * signature:
 *     (partner1: Partner, partner2: Partner, { env: OdooEnv, searchTerm: string, thread?: Thread , context?: Object}) => number|undefined
 */
export const partnerCompareRegistry = registry.category("mail.partner_compare");

partnerCompareRegistry.add(
    "mail.archived-last-except-odoobot",
    function archivedLastExceptOdoobot(p1, p2) {
        const p1active = p1.active || p1.eq(p1.store.odoobot);
        const p2active = p2.active || p2.eq(p2.store.odoobot);
        if (!p1active && p2active) {
            return 1;
        }
        if (!p2active && p1active) {
            return -1;
        }
        return undefined;
    },
    { sequence: 5 }
);

partnerCompareRegistry.add(
    "mail.self-last",
    function selfLast(p1, p2, { store }) {
        const isSelf1 = p1.eq(store.self);
        const isSelf2 = p2.eq(store.self);
        if (isSelf1 && !isSelf2) {
            return 1;
        }
        if (!isSelf1 && isSelf2) {
            return -1;
        }
        return undefined;
    },
    { sequence: 7 }
);

partnerCompareRegistry.add(
    "mail.recent-authors",
    function recentAuthors(p1, p2, { context: { latestMessageIdByAuthorId } }) {
        const p1MessageId = latestMessageIdByAuthorId.get(p1.id);
        const p2MessageId = latestMessageIdByAuthorId.get(p2.id);
        if (p1MessageId !== undefined && p2MessageId === undefined) {
            return -1;
        }
        if (p1MessageId === undefined && p2MessageId !== undefined) {
            return 1;
        }
        if (p1MessageId !== undefined && p2MessageId !== undefined && p1MessageId !== p2MessageId) {
            return p2MessageId - p1MessageId;
        }
        return undefined;
    },
    { sequence: 10 }
);

partnerCompareRegistry.add(
    "mail.internal-users",
    function internalUsers(p1, p2) {
        const isAInternalUser = p1.main_user_id?.share === false;
        const isBInternalUser = p2.main_user_id?.share === false;
        if (isAInternalUser && !isBInternalUser) {
            return -1;
        }
        if (!isAInternalUser && isBInternalUser) {
            return 1;
        }
        return undefined;
    },
    { sequence: 35 }
);

partnerCompareRegistry.add(
    "mail.followers",
    function followers(p1, p2, { thread }) {
        if (!thread) {
            return undefined;
        }
        const followerList = [...thread.followers];
        if (thread.selfFollower) {
            followerList.push(thread.selfFollower);
        }
        const isFollower1 = followerList.some((follower) => p1.eq(follower.partner_id));
        const isFollower2 = followerList.some((follower) => p2.eq(follower.partner_id));
        if (isFollower1 && !isFollower2) {
            return -1;
        }
        if (!isFollower1 && isFollower2) {
            return 1;
        }
        return undefined;
    },
    { sequence: 25 }
);

partnerCompareRegistry.add(
    "mail.name",
    function name(p1, p2, { searchTerm, thread }) {
        const name1 = thread?.getPersonaName(p1) ?? p1.displayName;
        const name2 = thread?.getPersonaName(p2) ?? p2.displayName;
        // no names to compare: not applicable.
        if (!name1 && !name2) {
            return undefined;
        }
        // 1. prioritize partners with a name over those without
        if (name1 && !name2) {
            return -1;
        }
        if (!name1 && name2) {
            return 1;
        }
        const normalizedName1 = normalize(name1);
        const normalizedName2 = normalize(name2);
        // 2. partners whose name starts with the search terms
        if (normalizedName1.startsWith(searchTerm) && !normalizedName2.startsWith(searchTerm)) {
            return -1;
        }
        if (!normalizedName1.startsWith(searchTerm) && normalizedName2.startsWith(searchTerm)) {
            return 1;
        }
        // 3. locale-sensitive alphabetical order
        return localeCompare(name1, name2) || undefined;
    },
    { sequence: 50 }
);

partnerCompareRegistry.add(
    "mail.email",
    function email(p1, p2, { searchTerm }) {
        const email1 = p1.displayEmail;
        const email2 = p2.displayEmail;
        // no emails to compare: not applicable
        if (!email1 && !email2) {
            return undefined;
        }
        // 1. prioritize partners with an email over those without
        if (email1 && !email2) {
            return -1;
        }
        if (!email1 && email2) {
            return 1;
        }
        const normalizedEmail1 = normalize(email1);
        const normalizedEmail2 = normalize(email2);
        // 2. partners whose email starts with the search terms
        if (normalizedEmail1.startsWith(searchTerm) && !normalizedEmail2.startsWith(searchTerm)) {
            return -1;
        }
        if (!normalizedEmail1.startsWith(searchTerm) && normalizedEmail2.startsWith(searchTerm)) {
            return 1;
        }
        // 3. locale-sensitive alphabetical order
        return localeCompare(email1, email2) || undefined;
    },
    { sequence: 55 }
);

partnerCompareRegistry.add("mail.id", (p1, p2) => p1.id - p2.id, { sequence: 75 });
