import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
    }

    /** @param {import("models").MessageReactions} reaction */
    getReactionSummary(reaction) {
        const [firstUserName, secondUserName, thirdUserName] = reaction.personas.map(
            ({ name, displayName }) => name || displayName
        );
        switch (reaction.count) {
            case 1:
                return _t("%(user)s has reacted with %(reaction)s", {
                    user: firstUserName,
                    reaction: reaction.content,
                });
            case 2:
                return _t("%(user1)s and %(user2)s have reacted with %(reaction)s", {
                    user1: firstUserName,
                    user2: secondUserName,
                    reaction: reaction.content,
                });
            case 3:
                return _t("%(user1)s, %(user2)s, %(user3)s have reacted with %(reaction)s", {
                    user1: firstUserName,
                    user2: secondUserName,
                    user3: thirdUserName,
                    reaction: reaction.content,
                });
            case 4:
                return _t(
                    "%(user1)s, %(user2)s, %(user3)s and 1 other person have reacted with %(reaction)s",
                    {
                        user1: firstUserName,
                        user2: secondUserName,
                        user3: thirdUserName,
                        reaction: reaction.content,
                    }
                );
            default:
                return _t(
                    "%(user1)s, %(user2)s, %(user3)s and %(count)s other persons have reacted with %(reaction)s",
                    {
                        user1: firstUserName,
                        user2: secondUserName,
                        user3: thirdUserName,
                        count: reaction.personas.length - 3,
                        reaction: reaction.content,
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
