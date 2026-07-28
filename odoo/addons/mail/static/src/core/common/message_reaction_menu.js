/* @odoo-module */

import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { onExternalClick } from "@mail/utils/common/hooks";

import {
    Component,
    onWillStart,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionMenu extends Component {
    static props = ["close", "message"];
    static components = { Dialog };
    static template = "mail.MessageReactionMenu";

    setup() {
        this.threadService = useService("mail.thread");
        this.root = useRef("root");
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.messageService = useService("mail.message");
        this.state = useState({
            reaction: this.props.message.reactions[0],
        });
        useExternalListener(document, "keydown", this.onKeydown);
        onExternalClick("root", () => this.props.close());
        useEffect(
            () => {
                const activeReaction = this.props.message.reactions.find(
                    ({ content }) => content === this.state.reaction.content
                );
                if (this.props.message.reactions.length === 0) {
                    this.props.close();
                } else if (!activeReaction) {
                    this.state.reaction = this.props.message.reactions[0];
                }
            },
            () => [this.props.message.reactions.length]
        );
        onWillStart(async () => {
            const { emojis } = await loadEmoji();
            this.emojis = emojis;
        });
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "Escape":
                this.props.close();
                break;
            case "q":
                this.props.close();
                break;
            default:
                return;
        }
    }

    getEmojiShortcode(reaction) {
        return this.emojis.find((emoji) => emoji.codepoints === reaction.content).shortcodes[0];
    }
}
