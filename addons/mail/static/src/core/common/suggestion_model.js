import { OR, Record } from "@mail/core/common/record";

export class Suggestion extends Record {
    static id = OR("mention", "channelCommand", "cannedResponse");
    /** @type {Object.<number, import("models").Suggestion>} */
    static records = {};
    /** @returns {import("models").Suggestion} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Suggestion|import("models").Suggestion[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new() {
        return super.new(...arguments);
    }

    mention = Record.one("Mention");
    channelCommand;
    cannedResponse = Record.one("CannedResponse");

    get type() {
        if (this.mention) {
            return "mention";
        }
        if (this.channelCommand) {
            return "channelCommand";
        }
        if (this.cannedResponse) {
            return "cannedResponse";
        }
        return undefined;
    }

    get navigableListInfo() {
        switch (this.type) {
            case "mention":
                return this.mention.navigableListInfo;
            case "channelCommand":
                return {
                    label: this.channelCommand.name,
                    help: this.channelCommand.help,
                    optionTemplate: "mail.Composer.suggestionChannelCommand",
                };
            case "cannedResponse":
                return {
                    cannedResponse: this.cannedResponse,
                    source: this.cannedResponse.source,
                    label: this.cannedResponse.substitution,
                    optionTemplate: "mail.Composer.suggestionCannedResponse",
                };
        }
        return undefined;
    }
}

Suggestion.register();
