import { Plugin } from "@html_editor/plugin";

import { localeCompare, normalize } from "@web/core/l10n/utils";

/** Suggests the commands of a channel, typed at the start of its composer. */
export class ChannelCommandSuggestionPlugin extends Plugin {
    static id = "channelCommandSuggestion";
    /** @type {import("plugins").EditorResources} */
    resources = {
        suggestion_sources: {
            allowedPosition: 0,
            delimiter: "/",
            isAvailable: () => Boolean(this.getChannel()),
            keepsDelimiter: true,
            search: (cleanedTerm) => this.search(cleanedTerm),
            toOptions: (commands) => ({
                optionTemplate: "mail.Composer.suggestionChannelCommand",
                options: commands.map((command) => ({ help: command.help, label: command.name })),
            }),
        },
    };

    getChannel() {
        return this.config.composerPluginDependencies.getThread()?.channel;
    }

    /** @param {string} cleanedTerm */
    search(cleanedTerm) {
        const commands = (this.getChannel()?.getCommands() ?? []).filter(({ name }) =>
            normalize(name).includes(cleanedTerm)
        );
        const sortFunc = (c1, c2) => {
            const cleanedName1 = normalize(c1.name);
            const cleanedName2 = normalize(c2.name);
            if (cleanedName1.startsWith(cleanedTerm) && !cleanedName2.startsWith(cleanedTerm)) {
                return -1;
            }
            if (!cleanedName1.startsWith(cleanedTerm) && cleanedName2.startsWith(cleanedTerm)) {
                return 1;
            }
            return localeCompare(c1.name, c2.name) || c1.id - c2.id;
        };
        return commands.sort(sortFunc);
    }
}
