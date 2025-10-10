import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class MailSuggestionPlugin extends Plugin {
    static id = "mail_suggestion";
    static dependencies = ["powerbox"];
    static shared = ["openSuggestionPowerbox"];
    resources = {
        powerbox_categories: {
            id: "mail_suggestion_canned_response",
            name: _t("Canned Responses"),
        },
    };

    openSuggestionPowerbox(suggestion) {
        this.dependencies.powerbox.openPowerbox({
            commands: this.formatPowerboxCommands(suggestion),
        });
    }

    formatPowerboxCommands(suggestion) {
        const suggestions = suggestion.state.items.suggestions;
        switch (suggestion.state.items.type) {
            case "Partner":
                return suggestions.map((s) => {
                    if (s.isSpecial) {
                        return {
                            ...s,
                            commandId: s.id,
                            template: "mail.Composer.suggestionSpecial",
                            run: () => {
                                suggestion.insert({
                                    ...s,
                                });
                            },
                        };
                    } else if (s.Model.getName() === "res.role") {
                        return {
                            role: s,
                            thread: s.thread,
                            template: "mail.Composer.suggestionRole",
                            run: () => {
                                suggestion.insert({
                                    role: s,
                                    label: s.name,
                                });
                            },
                        };
                    } else {
                        return {
                            partner: s,
                            template: "mail.Composer.suggestionPartner",
                            run: () => {
                                suggestion.insert({
                                    partner: s,
                                    label: s.name,
                                });
                            },
                        };
                    }
                });
            case "Thread":
                return suggestions.map((s) => ({
                    commandId: s.id,
                    template: "mail.Composer.suggestionThread",
                    thread: s,
                    run: () => {
                        suggestion.insert({
                            thread: s,
                            label: s.fullNameWithParent,
                        });
                    },
                }));
            case "ChannelCommand":
                return suggestions.map((s) => ({
                    commandId: s.id,
                    icon: s.icon,
                    title: s.name,
                    description: s.help,
                    run: () => {
                        suggestion.insert({
                            channelCommand: s,
                            label: s.name,
                        });
                    },
                }));
            case "mail.canned.response": {
                return suggestions.map((s) => ({
                    commandId: s.id,
                    template: "mail.Composer.suggestionCannedResponse",
                    source: s.source,
                    label: s.substitution,
                    run: () => {
                        suggestion.insert({
                            cannedResponse: s,
                            label: s.substitution,
                        });
                    },
                }));
            }
            case "emoji":
                return suggestions.map((s) => ({
                    commandId: s.id,
                    template: "mail.Composer.suggestionEmoji",
                    emoji: s,
                    run: () => {
                        suggestion.insert({
                            emoji: s,
                            label: s.codepoints,
                        });
                    },
                }));
            default:
                return [];
        }
    }
}
