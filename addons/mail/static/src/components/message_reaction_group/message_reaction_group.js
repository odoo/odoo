/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isUnicodeInOdooEmojisSelection, getEmojiClassName, getEmoji } from "@mail/emojis/emojis"

export class MessageReactionGroup extends Component {

    setup() {
        this.messageReactionGroup = this.messaging.models['mail.message_reaction_group'].get(this.props.messageReactionGroupLocalId);
        if (isUnicodeInOdooEmojisSelection(this.messageReactionGroup.content)) {
            const emoji = getEmoji(this.messageReactionGroup.content);
            this.emojiClass = getEmojiClassName(emoji);
            this.emojiUnicode = emoji.unicode;
        }
    }

}

Object.assign(MessageReactionGroup, {
    props: {
        messageReactionGroupLocalId: String,
    },
    template: 'mail.MessageReactionGroup',
});

registerMessagingComponent(MessageReactionGroup);
