import { Component, useRef } from "@odoo/owl";

import { MessageReactionList } from "@mail/core/common/message_reaction_list";
import { useService } from "@web/core/utils/hooks";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class MessageReactions extends Component {
    static props = ["message", "openReactionMenu"];
    static template = "mail.MessageReactions";
    static components = { MessageReactionList };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.addRef = useRef("add");
        this.isMobileOS = isMobileOS();
        this.emojiPicker = useEmojiPicker(this.addRef, {
            onSelect: (emoji) => {
                const reaction = this.props.message.reactions.find(
                    ({ content, partner_ids, guest_ids }) =>
                        content === emoji &&
                        (partner_ids.find((partner) => partner.eq(this.store.self_partner)) ||
                            guest_ids.find((guest) => guest.eq(this.store.self_guest)))
                );
                if (!reaction) {
                    this.props.message.react(emoji);
                }
            },
        });
    }
}
