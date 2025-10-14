import { Plugin } from "@html_editor/plugin";

export class MailSuggestionPartnerPlugin extends Plugin {
    static id = "mail_suggestion_partner";
    static dependencies = ["mail_suggestion"];
    resources = {
        mail_suggestion_type_formatters: {
            type: "Partner",
            formatter: (useSuggestion) => {
                const suggestions = useSuggestion.state.items.suggestions;
                return suggestions.map((suggestion) => {
                    if (suggestion.isSpecial) {
                        return {
                            commandId: suggestion.id,
                            template: "mail.Composer.suggestionSpecial",
                            props: {
                                option: { ...suggestion },
                            },
                            run: () => {
                                useSuggestion.insert({
                                    ...suggestion,
                                });
                            },
                        };
                    } else if (suggestion.Model.getName() === "res.role") {
                        return {
                            commandId: suggestion.id,
                            template: "mail.Composer.suggestionRole",
                            props: {
                                option: { label: suggestion.name, thread: suggestion.thread },
                            },
                            run: () => {
                                useSuggestion.insert({
                                    role: suggestion,
                                    label: suggestion.name,
                                });
                            },
                        };
                    } else {
                        return {
                            commandId: suggestion.id,
                            template: "mail.Composer.suggestionPartner",
                            props: {
                                option: { partner: suggestion, showImStatus: false },
                            },
                            run: () => {
                                useSuggestion.insert({
                                    partner: suggestion,
                                    label: suggestion.name,
                                });
                            },
                        };
                    }
                });
            },
        },
    };
}
