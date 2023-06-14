/* @odoo-module */

import {
    getSupportedSuggestionDelimiters,
    searchSuggestions,
} from "@mail/core/common/suggestion_service";
import { cleanTerm } from "@mail/utils/common/format";
import { patchFn } from "@mail/utils/common/patch";

import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

patchFn(getSupportedSuggestionDelimiters, function (thread) {
    const res = this._super(thread);
    return thread?.model === "discuss.channel" ? [...res, ["/", 0]] : res;
});

patchFn(searchSuggestions, function ({ delimiter, term }, { thread } = {}, sort = false) {
    if (delimiter === "/") {
        return searchChannelCommand(cleanTerm(term), thread, sort);
    }
    return this._super(...arguments);
});

function searchChannelCommand(cleanedSearchTerm, thread, sort) {
    if (!thread.isChannel) {
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
        const cleanedName1 = cleanTerm(c1.name || "");
        const cleanedName2 = cleanTerm(c2.name || "");
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
}
