/* @odoo-module */

import { SuggestionService } from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(SuggestionService.prototype, {
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
                    return command.channel_types.includes(thread.type);
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
            mainSuggestions: sort ? commands.sort(sortFunc) : commands,
        };
    },
});
