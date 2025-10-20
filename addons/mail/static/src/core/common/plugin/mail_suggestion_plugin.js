import { Plugin } from "@html_editor/plugin";

export class MailSuggestionPlugin extends Plugin {
    static id = "mail_suggestion";
    static dependencies = ["powerbox"];
    static shared = ["openSuggestionPowerbox"];

    openSuggestionPowerbox(useSuggestion) {
        const commands = this.formatPowerboxCommands(useSuggestion);
        if (!commands || commands.length === 0) {
            return;
        }
        this.dependencies.powerbox.openPowerbox({
            commands,
        });
    }

    formatPowerboxCommands(useSuggestion) {
        const mailSuggestionTypeFormatters = this.getResource("mail_suggestion_type_formatters");
        const mailSuggestionTypeFormatterDict = Object.fromEntries(
            mailSuggestionTypeFormatters.map((typeFormatter) => [
                typeFormatter.type,
                typeFormatter.formatter,
            ])
        );
        return mailSuggestionTypeFormatterDict[useSuggestion.state.items.type]?.(useSuggestion);
    }
}
