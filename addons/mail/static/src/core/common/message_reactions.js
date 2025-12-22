import { Component, useRef, useState } from "@odoo/owl";

import { MessageReactionList } from "@mail/core/common/message_reaction_list";
import { useService } from "@web/core/utils/hooks";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";
    static components = { MessageReactionList };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.addRef = useRef("add");
        this.emojiPicker = useEmojiPicker(this.addRef, {
            onSelect: (emoji) => {
                const reaction = this.props.message.reactions.find(
                    ({ content, personas }) =>
                        content === emoji && this.props.message.effectiveSelf.in(personas)
                );
                if (!reaction) {
                    this.props.message.react(emoji);
                }
            },
        });
    }
}
