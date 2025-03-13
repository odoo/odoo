import { SuggestionService } from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getSupportedDelimiters(thread) {
        const res = super.getSupportedDelimiters(thread);
        return thread?.model === "discuss.channel" ? [...res, ["/", 0]] : res;
    },
    /**
     * @override
     */
    isSuggestionValid(persona, thread) {
        if (thread?.model === "discuss.channel" && persona.eq(this.store.odoobot)) {
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
            let partners = thread.channel_member_ids
                .map((member) => member.persona)
                .filter((persona) => persona.type === "partner");
            if (thread.channel_type === "channel") {
                const group = (thread.parent_channel_id || thread).group_public_id;
                partners = new Set([...partners, ...(group?.personas ?? [])]);
            }
            return partners;
        } else {
            return super.getPartnerSuggestions(...arguments);
        }
    },
    /**
     * @override
     */
    searchSuggestions({ delimiter, term }, { thread, sort = false } = {}) {
        if (delimiter === "/") {
            return this.searchChannelCommand(cleanTerm(term), thread, sort);
        }
        return super.searchSuggestions(...arguments);
    },
    searchChannelCommand(cleanedSearchTerm, thread, sort) {
        if (!thread.model === "discuss.channel") {
            // channel commands are channel specific
            return;
        }
        const commands = commandRegistry
            .getEntries()
            .filter(([name, command]) => {
                if (!cleanTerm(name).includes(cleanedSearchTerm)) {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(thread.channel_type);
                }
                return true;
            })
            .map(([name, command]) => {
                return {
                    channel_types: command.channel_types,
                    help: command.help,
                    id: command.id,
                    name,
                };
            });
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
            suggestions: sort ? commands.sort(sortFunc) : commands,
        };
    },
    /** @override */
    sortPartnerSuggestionsContext(thread) {
        return Object.assign(super.sortPartnerSuggestionsContext(), {
            recentChatPartnerIds: this.store.getRecentChatPartnerIds(),
            memberPartnerIds: new Set(
                thread?.channel_member_ids
                    .filter((member) => member.persona.type === "partner")
                    .map((member) => member.persona.id)
            ),
        });
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
