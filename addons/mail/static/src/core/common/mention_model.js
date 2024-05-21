import { OR, Record } from "@mail/core/common/record";
import { _t } from "@web/core/l10n/translation";

export class Mention extends Record {
    static id = OR("channel", "partner", "special");
    /** @type {Object.<number, import("models").Mention>} */
    static records = {};
    /** @returns {import("models").Mention} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Mention|import("models").Mention[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new() {
        return super.new(...arguments);
    }

    static specialMentions = {
        everyone: {
            label: "everyone",
            channel_types: ["channel", "group"],
            displayName: "Everyone",
            description: _t("Notify everyone"),
        },
    };

    channel = Record.one("Thread");
    partner = Record.one("Persona");
    /** @type {'everyone' | 'here' | 'admins'} */
    special;

    get type() {
        if (this.channel) {
            return "channel";
        }
        if (this.partner) {
            return "partner";
        }
        if (this.special) {
            return "special";
        }
        return undefined;
    }

    get navigableListInfo() {
        switch (this.type) {
            case "channel":
                return {
                    mention: this,
                    label: this.channel.displayName,
                    thread: this.channel,
                    optionTemplate: "mail.Composer.suggestionThread",
                };
            case "partner":
                return {
                    mention: this,
                    label: this.partner.name,
                    partner: this.partner,
                    optionTemplate: "mail.Composer.suggestionPartner",
                };
            case "special":
                return {
                    mention: this,
                    isSpecial: true,
                    navigableListGroup: 1,
                    ...Mention.specialMentions[this.special],
                    optionTemplate: "mail.Composer.suggestionSpecial",
                };
        }
        return undefined;
    }
}

Mention.register();
