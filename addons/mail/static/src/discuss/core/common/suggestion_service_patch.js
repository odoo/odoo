import { SuggestionService } from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");
const mailSuggestionsRegistry = registry.category("mail.suggestions");

mailSuggestionsRegistry.add("command", {
    name: _t("Channel Command"),
    sequence: 1,
});

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getSupportedDelimiters(thread) {
        const res = super.getSupportedDelimiters(thread);
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
            .map(([name, command]) => ({
                channel_types: command.channel_types,
                help: command.help,
                id: command.id,
                icon: command.icon,
                name,
            }));
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
        return sort
            ? [
                  ...commands.sort(sortFunc).map((c) => ({
                      title: c.name,
                      description: c.help,
                      categoryId: "command",
                      command: c,
                  })),
              ]
            : [
                  ...commands.map((c) => ({
                      title: c.name,
                      description: c.help,
                      categoryId: "command",
                      command: c,
                  })),
              ];
    },
    /** @override */
    sortPartnerSuggestionsContext() {
        return Object.assign(super.sortPartnerSuggestionsContext(), {
            recentChatPartnerIds: this.store.getRecentChatPartnerIds(),
        });
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
