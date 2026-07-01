import { useRef } from "@web/owl2/utils";
import { Component, props, t } from "@odoo/owl";

import { useMessageActions } from "@mail/core/common/message_actions";
import { MessageReactionList, openReactionMenuType } from "@mail/core/common/message_reaction_list";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { propComputed } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class MessageReactions extends Component {
    static template = "mail.MessageReactions";
    static components = { MessageReactionList, QuickReactionMenu };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.message = propComputed("message", t.instanceOf(this.store["mail.message"].Class));
        this.openReactionMenu = props.static("openReactionMenu", openReactionMenuType(this.store));
        this.ui = useService("ui");
        this.addRef = useRef("add");
        this.isMobileOS = isMobileOS();
        this.messageActions = useMessageActions({ message: this.message });
        this.emojiPicker = useEmojiPicker(this.addRef, {
            onSelect: (emoji) => {
                const reaction = this.message().reactions.find(
                    ({ content, personas }) =>
                        content === emoji && this.message().effectiveSelf.in(personas)
                );
                if (!reaction) {
                    this.message().react(emoji);
                }
            },
        });
    }
}
