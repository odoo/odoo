import { Component, useState } from "@odoo/owl";

import { MessageReactionList } from "@mail/core/common/message_reaction_list";
import { useService } from "@web/core/utils/hooks";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";
    static components = { MessageReactionList };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
    }
}
