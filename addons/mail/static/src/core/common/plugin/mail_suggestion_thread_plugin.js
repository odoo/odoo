import { Plugin } from "@html_editor/plugin";

export class MailSuggestionThreadPlugin extends Plugin {
    static id = "mail_suggestion_thread";
    static dependencies = ["mail_suggestion"];
    resources = {
        mail_suggestion_type_formatters: {
            type: "Thread",
            formatter: (useSuggestion) => {
                const suggestions = useSuggestion.state.items.suggestions;
                return suggestions.map((suggestion) => ({
                    commandId: suggestion.id,
                    template: "mail.Composer.suggestionThread",
                    props: {
                        option: { thread: suggestion },
                    },
                    run: () => {
                        useSuggestion.insert({
                            thread: suggestion,
                            label: suggestion.fullNameWithParent,
                        });
                    },
                }));
            },
        },
    };
}
