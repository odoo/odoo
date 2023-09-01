/* @odoo-module */

import { usePopover } from "@web/core/popover/popover_hook";
import { MessageReactionList } from "@mail/core/common/message_reaction_list";
import { browser } from "@web/core/browser/browser";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";
    static components = { MessageReactionList };

    setup() {
        this.user = useService("user");
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.messageService = useState(useService("mail.message"));
        this.reactionOpened = false;
        this.reactionPopover = usePopover(MessageReactionList, {
            closeOnHoverAway: true,
            popoverClass: "o-mail-MessageReactionList-Popover",
            position: "bottom-start",
        });
        this.lastedOpenedId = 0;
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

    openCard(params) {
        const target = params.ev.currentTarget;
        const reaction = params.reaction;
        this.reactionOpened = browser.setTimeout(() => {
            if (
                !this.reactionPopover.isOpen ||
                (this.lastOpenedId && reaction.messageId !== this.lastOpenedId)
            ) {
                this.reactionPopover.open(target, {
                    id: reaction.messageId,
                    reaction: params.reaction,
                    openReactionMenu: this.props.openReactionMenu,
                });
                this.lastOpenId = reaction.messageId;
            }
        }, 350);
    }

    clearTimeout() {
        browser.clearTimeout(this.reactionOpened);
        delete this.reactionOpened;
    }
}
