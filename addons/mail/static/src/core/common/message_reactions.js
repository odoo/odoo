import { Component, useRef } from "@odoo/owl";

import { useMessageActions } from "@mail/core/common/message_actions";
import { MessageReactionList } from "@mail/core/common/message_reaction_list";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { useService } from "@web/core/utils/hooks";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";
    static components = { MessageReactionList, QuickReactionMenu };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.addRef = useRef("add");
        this.isMobileOS = isMobileOS();
        this.messageActions = useMessageActions({ message: () => this.props.message });
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
