import { Plugin } from "@html_editor/plugin";

export class MailSuggestionEmojiPlugin extends Plugin {
    static id = "mail_suggestion_emoji";
    static dependencies = ["mail_suggestion"];
    resources = {
        mail_suggestion_type_formatters: {
            type: "emoji",
            formatter: (useSuggestion) => {
                const suggestions = useSuggestion.state.items.suggestions;
                return suggestions.map((suggestion) => ({
                    commandId: suggestion.id,
                    template: "mail.Composer.suggestionEmoji",
                    props: {
                        option: { emoji: suggestion },
                    },
                    run: () => {
                        useSuggestion.insert({
                            emoji: suggestion,
                            label: suggestion.codepoints,
                        });
                    },
                }));
            },
        },
    };
}
