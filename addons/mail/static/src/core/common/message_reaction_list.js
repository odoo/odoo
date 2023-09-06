/* @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class MessageReactionList extends Component {
    static template = "mail.MessageReaction.List";
    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        reaction: { type: Object, required: true },
        openReactionMenu: { type: Function, required: true },
    };

    getReactionSummary() {
        const reaction = this.props.reaction;
        const [firstUserName, secondUserName, thirdUserName] = reaction.personas.map(
            ({ name, displayName }) => name || displayName
        );
        switch (reaction.count) {
            case 1:
                return _t("%s has reacted with %s", firstUserName, reaction.content);
            case 2:
                return _t(
                    "%s and %s have reacted with %s",
                    firstUserName,
                    secondUserName,
                    reaction.content
                );
            case 3:
                return _t(
                    "%s, %s, %s have reacted with %s",
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.content
                );
            default:
                return {
                    names: _t("%s, %s, %s and ", firstUserName, secondUserName, thirdUserName),
                    highlightText: _t("%s other", reaction.personas.length - 3),
                    content: _t(" persons have reacted with %s", reaction.content),
                };
        }
    }

    manageReactionMenu() {
        this.props.openReactionMenu();
        this.props.close();
    }

    highlightSummary(ev) {
        const { reaction } = this.props;
        if (reaction.count > 3) {
            ev.target.classList.toggle("active");
        }
    }
}
