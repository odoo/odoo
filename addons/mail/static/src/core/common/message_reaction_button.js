import { Component, useRef, useState } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @extends {Component<Props, Env>}
 */
export class MessageReactionButton extends Component {
    static template = "mail.MessageReactionButton";
    static props = ["message", "classNames?", "action"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.emojiPickerRef = useRef("emoji-picker");
        this.emojiPicker = useEmojiPicker(this.emojiPickerRef, {
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
