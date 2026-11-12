import { Component, t } from "@odoo/owl";

import { useMessageActions } from "@mail/core/common/message_actions";
import { MessageReactionList, openReactionMenuType } from "@mail/core/common/message_reaction_list";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { propComputed, propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static template = "mail.MessageReactions";
    static components = { MessageReactionList, QuickReactionMenu };

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            hasActions: propComputed(t.boolean().optional(true)),
            isReadOnly: propStatic(t.signal(t.boolean())),
            message: propComputed(t.instanceOf(this.store["mail.message"])),
            openReactionMenu: propStatic(openReactionMenuType(this.store)),
        });
        this.messageActions = useMessageActions({ message: this.props.message });
    }

    get hasQuickReaction() {
        return (
            this.props.message().canAddReaction &&
            !this.props.isReadOnly() &&
            !(this.props.hasActions() && this.props.message().hasActions)
        );
    }
}
