import { SuggestionService } from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getChannelCommands(thread) {
        if (!thread || thread.model !== "discuss.channel") {
            return [];
        }
        return commandRegistry
            .getEntries()
            .map(([name, command]) => ({
                channel_types: command.channel_types,
                condition: command.condition,
                help: command.help,
                id: command.id,
                name,
            }))
            .filter(({ condition, channel_types }) => {
                const passesCondition = !condition || condition({ store: this.store, thread });
                const passesChannelType =
                    !channel_types || channel_types.includes(thread.channel_type);
                return passesCondition && passesChannelType;
            });
    },
    getSupportedDelimiters(thread, env) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread?.model === "discuss.channel" ? [...res, ["/", 0]] : res;
    },
    /**
     * @override
     */
    isSuggestionValid(partner, thread) {
        if (thread?.model === "discuss.channel" && partner.eq(this.store.odoobot)) {
            return true;
        }
        return super.isSuggestionValid(...arguments);
    },
    /**
     * @override
     */
    getPartnerSuggestions(thread) {
        const isNonPublicChannel =
            thread &&
            (thread.channel_type === "group" ||
                thread.channel_type === "chat" ||
                (thread.channel_type === "channel" &&
                    (thread.parent_channel_id || thread).group_public_id));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            const partnersById = new Map(
                [
                    ...thread.channel_member_ids,
                    ...(thread.parent_channel_id?.channel_member_ids ?? []),
                ]
                    .filter((m) => m.partner_id)
                    .map((m) => [m.partner_id.id, m.partner_id])
            );
            if (thread.channel_type === "channel") {
                const group = (thread.parent_channel_id || thread).group_public_id;
                group.partners.forEach((partner) => partnersById.set(partner.id, partner));
            }
            return Array.from(partnersById.values());
        } else {
            return super.getPartnerSuggestions(...arguments);
        }
    },
    /**
     * @override
     */
    searchSuggestions({ delimiter, term }, { thread } = {}) {
        if (delimiter === "/") {
            return this.searchChannelCommand(cleanTerm(term), thread);
        }
        return super.searchSuggestions(...arguments);
    },
    searchChannelCommand(cleanedSearchTerm, thread) {
        if (!thread.model === "discuss.channel") {
            // channel commands are channel specific
            return;
        }
        const commands = this.getChannelCommands(thread).filter(({ name }) =>
            cleanTerm(name).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            if (c1.channel_types && !c2.channel_types) {
                return -1;
            }
            if (!c1.channel_types && c2.channel_types) {
                return 1;
            }
            const cleanedName1 = cleanTerm(c1.name);
            const cleanedName2 = cleanTerm(c2.name);
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
            type: "ChannelCommand",
            suggestions: commands.sort(sortFunc),
        };
    },
    /** @override */
    sortPartnerSuggestionsContext(thread) {
        return Object.assign(super.sortPartnerSuggestionsContext(), {
            recentChatPartnerIds: this.store.getRecentChatPartnerIds(),
            memberPartnerIds: new Set(
                thread?.channel_member_ids
                    .filter((member) => member.partner_id)
                    .map((member) => member.partner_id.id)
            ),
        });
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
