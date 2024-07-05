import { useHover } from "@mail/utils/common/hooks";
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionList extends Component {
    static template = "mail.MessageReactionList";
    static components = { Dropdown };
    static props = ["message", "openReactionMenu", "reaction"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.hover = useHover(["reactionButton", "reactionList*"], () => {
            if (!this.hover.isHover) {
                clearTimeout(this.showReactionListTimeout);
                this.showReactionListTimeout = setTimeout(() => (this.preview.isOpen = false), 50);
            } else {
                clearTimeout(this.showReactionListTimeout);
                this.preview.isOpen = true;
            }
        });
        this.preview = useDropdownState();
    }

    /** @param {import("models").MessageReactions} reaction */
    previewText(reaction) {
        const { count, content: emoji } = reaction;
        const personNames = reaction.personas
            .map(({ name, displayName }) => name || displayName)
            .slice(0, 3);
        switch (count) {
            case 1:
                return _t("%(emoji)s reacted by %(person)s", { emoji, person: personNames[0] });
            case 2:
                return _t("%(emoji)s reacted by %(person1)s and %(person2)s", {
                    emoji,
                    person1: personNames[0],
                    person2: personNames[1],
                });
            case 3:
                return _t("%(emoji)s reacted by %(person1)s, %(person2)s, and %(person3)s", {
                    emoji,
                    person1: personNames[0],
                    person2: personNames[1],
                    person3: personNames[2],
                });
            case 4:
                return _t(
                    "%(emoji)s reacted by %(person1)s, %(person2)s, %(person3)s, and 1 other",
                    {
                        emoji,
                        person1: personNames[0],
                        person2: personNames[1],
                        person3: personNames[2],
                    }
                );
            default:
                return _t(
                    "%(emoji)s reacted by%(person1)s, %(person2)s, %(person3)s, and %(count)s others",
                    {
                        count: count - 3,
                        emoji,
                        person1: personNames[0],
                        person2: personNames[1],
                        person3: personNames[2],
                    }
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
