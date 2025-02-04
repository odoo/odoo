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
