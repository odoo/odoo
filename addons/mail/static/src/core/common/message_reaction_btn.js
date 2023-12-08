import { useHover } from "@mail/utils/common/hooks";
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionBtn extends Component {
    static components = { Dropdown };
    static props = ["reaction"];
    static template = "mail.messageReactionBtn";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.wasHover = false;
        this.hover = useHover(["root", "preview*"], () => {
            this.preview.isOpen = this.hover.isHover;
            if (this.hover.isHover && !this.wasHover) {
                clearTimeout(this.showCloseTimeout);
                this.showCloseTimeout = setTimeout(() => (this.state.showClose = true), 50);
            } else if (!this.hover.isHover) {
                clearTimeout(this.showCloseTimeout);
                this.state.showClose = false;
            }
            this.wasHover = this.hover.isHover;
        });
        this.preview = useDropdownState();
        this.state = useState({ bouncing: false, showClose: true });
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
                    "%s, %s, %s and %s othr persons have reacted with %s",
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
            reaction.remove();
        } else {
            this.props.message.react(reaction.content);
        }
    }

    onContextMenu(ev) {
        if (this.ui.isSmall) {
            ev.preventDefault();
            this.props.openReactionMenu();
        }
    }
}
