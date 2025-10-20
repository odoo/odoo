import { Plugin } from "@html_editor/plugin";

export class MailSuggestionCannedResponsePlugin extends Plugin {
    static id = "mail_suggestion_canned_response";
    static dependencies = ["mail_suggestion"];
    resources = {
        mail_suggestion_type_formatters: {
            type: "mail.canned.response",
            formatter: (useSuggestion) => {
                const suggestions = useSuggestion.state.items.suggestions;
                return suggestions.map((suggestion) => ({
                    commandId: suggestion.id,
                    template: "mail.Composer.suggestionCannedResponse",
                    props: {
                        option: { source: suggestion.source, label: suggestion.substitution },
                    },
                    run: () => {
                        useSuggestion.insert({
                            cannedResponse: suggestion,
                            label: suggestion.substitution,
                        });
                    },
                }));
            },
        },
    };
}
