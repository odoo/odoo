import { Plugin } from "@html_editor/plugin";

export class MailSuggestionChannelCommandPlugin extends Plugin {
    static id = "mail_suggestion_channel_command";
    static dependencies = ["mail_suggestion"];
    resources = {
        mail_suggestion_type_formatters: {
            type: "ChannelCommand",
            formatter: (useSuggestion) => {
                const suggestions = useSuggestion.state.items.suggestions;
                return suggestions.map((suggestion) => ({
                    commandId: suggestion.id,
                    icon: suggestion.icon,
                    title: suggestion.name,
                    description: suggestion.help,
                    run: () => {
                        useSuggestion.insert({
                            channelCommand: suggestion,
                            label: suggestion.name,
                        });
                    },
                }));
            },
        },
    };
}
