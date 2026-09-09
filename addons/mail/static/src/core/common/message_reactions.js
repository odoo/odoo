import { Component, t, useProps } from "@odoo/owl";

import { useMessageActions } from "@mail/core/common/message_actions";
import { MessageReactionList, openReactionMenuType } from "@mail/core/common/message_reaction_list";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static template = "mail.MessageReactions";
    static components = { MessageReactionList, QuickReactionMenu };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            hasActions: t.signal(t.boolean()).optional(true),
            isReadOnly: t.signal(t.boolean()).optional(false),
            message: t.signal(t.instanceOf(this.store["mail.message"])),
            openReactionMenu: openReactionMenuType(this.store).static(),
        });
        this.messageActions = useMessageActions({ message: () => this.props.message() });
    }

    get hasQuickReaction() {
        return (
            this.props.message().canAddReaction &&
            !this.props.isReadOnly() &&
            !(this.props.hasActions() && this.props.message().hasActions)
        );
    }
}
