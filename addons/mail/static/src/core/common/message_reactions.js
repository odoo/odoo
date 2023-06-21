/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { reactToMessage, removeReaction } from "./message_service";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";

    setup() {
        this.user = useService("user");
        this.messaging = useService("mail.messaging");
        this.store = useStore();
        this.ui = useService("ui");
    }

    getReactionSummary(reaction) {
        const [firstUserName, secondUserName, thirdUserName] = reaction.personas.map(
            ({ name, displayName }) => name || displayName
        );
        switch (reaction.count) {
            case 1:
                return sprintf(_t("%s has reacted with %s"), firstUserName, reaction.content);
            case 2:
                return sprintf(
                    _t("%s and %s have reacted with %s"),
                    firstUserName,
                    secondUserName,
                    reaction.content
                );
            case 3:
                return sprintf(
                    _t("%s, %s, %s have reacted with %s"),
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.content
                );
            case 4:
                return sprintf(
                    _t("%s, %s, %s and 1 other person have reacted with %s"),
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.content
                );
            default:
                return sprintf(
                    _t("%s, %s, %s and %s other persons have reacted with %s"),
                    firstUserName,
                    secondUserName,
                    thirdUserName,
                    reaction.personas.length - 3,
                    reaction.content
                );
        }
    }

    hasSelfReacted(reaction) {
        return this.store.incl(reaction.personas, this.store.self);
    }

    onClickReaction(reaction) {
        if (this.hasSelfReacted(reaction)) {
            removeReaction(reaction);
        } else {
            reactToMessage(this.props.message, reaction.content);
        }
    }

    onContextMenu(ev) {
        if (this.ui.isSmall) {
            ev.preventDefault();
            this.props.openReactionMenu();
        }
    }
}
