/* @odoo-module */

import { Component, markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class MessageReactionList extends Component {
    static template = "mail.MessageReaction.List";
    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        reaction: { type: Object, required: true },
        openReactionMenu: { type: Function, required: true },
    };

    setup() {
        super.setup();
    }

    getReactionSummary() {
        const reaction = this.props.reaction;
        const [firstUserName, secondUserName, thirdUserName] = reaction.personas.map(
            ({ name, displayName }) => name || displayName
        );
        switch (reaction.count) {
            case 1:
                return markup(
                    _t(`<span>${firstUserName} has reacted with ${reaction.content}</span>`)
                );
            case 2:
                return markup(
                    _t(
                        `<span>${firstUserName} and ${secondUserName} has reacted with ${reaction.content}</span>`
                    )
                );
            case 3:
                return markup(
                    _t(
                        `<span>${firstUserName}, ${secondUserName} and ${thirdUserName} has reacted with ${reaction.content}</span>`
                    )
                );
            default:
                return markup(_t(`${firstUserName}, ${secondUserName}, ${thirdUserName} and `));
        }
    }

    manageReactionMenu() {
        this.props.openReactionMenu();
        this.props.close();
    }
}
