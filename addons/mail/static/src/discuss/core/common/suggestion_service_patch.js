import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";
import { SuggestionService } from "@mail/core/common/suggestion_service";

import { localeCompare, normalize } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getChannelCommands(channel) {
        if (!channel) {
            return [];
        }
        return commandRegistry
            .getEntries()
            .map(([name, command]) => ({
                condition: command.condition,
                help: command.help,
                id: command.id,
                name,
            }))
            .filter(({ condition }) => !condition || condition({ store: this.store, channel }));
    },
    getSupportedDelimiters(thread, owner) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread?.channel ? [...res, [SUGGESTION_DELIMITERS.CHANNEL_COMMAND, 0]] : res;
    },
    /**
     * @override
     */
    isPartnerSuggestionValid(partner, { composerType, thread }) {
        if (thread?.channel && partner.eq(this.store.odoobot)) {
            return true;
        }
        return super.isPartnerSuggestionValid(partner, { composerType, thread });
    },
    /**
     * @override
     */
    getPartnerSuggestions({ composerType, thread }) {
        const isNonPublicChannel =
            thread &&
            (thread.channel?.channel_type === "group" ||
                thread.channel?.channel_type === "chat" ||
                (thread.channel?.channel_type === "channel" &&
                    (thread.channel.parent_channel_id || thread).group_public_id));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            const partnersById = new Map(
                [
                    ...(thread.channel?.channel_member_ids ?? []),
                    ...(thread.channel?.parent_channel_id?.channel_member_ids ?? []),
                ]
                    .filter((m) => m.partner_id)
                    .map((m) => [m.partner_id.id, m.partner_id])
            );
            if (thread.channel?.channel_type === "channel") {
                const group = (thread.channel.parent_channel_id || thread).group_public_id;
                group.partners.forEach((partner) => partnersById.set(partner.id, partner));
            }
            return Array.from(partnersById.values());
        } else {
            return super.getPartnerSuggestions({ thread, composerType });
        }
    },
    /**
     * @override
     */
    searchSuggestions({ delimiter, term }, { composerType, thread } = {}) {
        if (delimiter === SUGGESTION_DELIMITERS.CHANNEL_COMMAND) {
            return this.searchChannelCommand(normalize(term), thread.channel);
        }
        return super.searchSuggestions(...arguments);
    },
    searchChannelCommand(cleanedSearchTerm, channel) {
        if (!channel) {
            // channel commands are channel specific
            return;
        }
        const commands = this.getChannelCommands(channel).filter(({ name }) =>
            normalize(name).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const cleanedName1 = normalize(c1.name);
            const cleanedName2 = normalize(c2.name);
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
            return localeCompare(c1.name, c2.name) || c1.id - c2.id;
        };
        return {
            type: "ChannelCommand",
            suggestions: commands.sort(sortFunc),
        };
    },
    /** @override */
    sortPartnerSuggestionsContext(thread) {
        return Object.assign(super.sortPartnerSuggestionsContext(...arguments), {
            recentChatPartnerIds: this.store.getRecentChatPartnerIds(),
            memberPartnerIds: new Set(
                thread?.channel?.channel_member_ids
                    .filter((member) => member.partner_id)
                    .map((member) => member.partner_id.id)
            ),
        });
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
