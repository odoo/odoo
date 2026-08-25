import { Component, t, useProps } from "@odoo/owl";

import { useMessageActions } from "@mail/core/common/message_actions";
import { MessageReactionList, openReactionMenuType } from "@mail/core/common/message_reaction_list";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { propComputed, propSignal } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static template = "mail.MessageReactions";
    static components = { MessageReactionList, QuickReactionMenu };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.hasActions = propComputed("hasActions", t.boolean().optional(true));
        this.message = propComputed("message", t.instanceOf(this.store["mail.message"]));
        this.isReadOnly = propSignal("isReadOnly", t.boolean().optional(false));
        this.openReactionMenu = useProps.static(
            "openReactionMenu",
            openReactionMenuType(this.store)
        );
        this.messageActions = useMessageActions({ message: this.message });
    }

    get hasQuickReaction() {
        return (
            this.message().canAddReaction &&
            !this.isReadOnly() &&
            !(this.hasActions() && this.message().hasActions)
        );
    }
}
