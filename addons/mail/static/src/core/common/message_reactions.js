/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";

    setup() {
        this.user = useService("user");
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.messageService = useState(useService("mail.message"));
    }

    /** @param {import("models").MessageReactions} reaction */
    getReactionSummary(reaction) {
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
            case 4:
                return _t(
                    "%s, %s, %s and 1 other person have reacted with %s",
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.content
                );
            default:
                return _t(
                    "%s, %s, %s and %s other persons have reacted with %s",
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.personas.length - 3,
                    reaction.content
                );
        }
    }

    hasSelfReacted(reaction) {
        return this.store.self.in(reaction.personas);
    }

    onClickReaction(reaction) {
        if (this.hasSelfReacted(reaction)) {
            this.messageService.removeReaction(reaction);
        } else {
            this.messageService.react(this.props.message, reaction.content);
        }
    }

    onContextMenu(ev) {
        if (this.ui.isSmall) {
            ev.preventDefault();
            this.props.openReactionMenu();
        }
    }
}
