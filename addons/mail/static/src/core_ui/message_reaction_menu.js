/** @odoo-module */

import {
    Component,
    useState,
    useExternalListener,
    useEffect,
    useRef,
    onWillStart,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { loadEmoji } from "@mail/emoji_picker/emoji_picker";
import { onExternalClick } from "@mail/utils/hooks";
import { useStore } from "../core/messaging_hook";

export class MessageReactionMenu extends Component {
    static props = ["close", "message"];
    static components = { Dialog };
    static template = "mail.MessageReactionMenu";

    setup() {
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.root = useRef("root");
        this.store = useStore();
        this.ui = useState(useService("ui"));
        this.messageService = useService("mail.message");
        this.state = useState({
            reaction: this.props.message.reactions[0],
        });
        useExternalListener(document, "keydown", this.onKeydown);
        onExternalClick("root", () => this.props.close());
        useEffect(
            (reactions) => {
                const activeReaction = reactions.find(
                    ({ content }) => content === this.state.reaction.content
                );
                if (reactions.length === 0) {
                    this.props.close();
                } else if (!activeReaction) {
                    this.state.reaction = reactions[0];
                }
            },
            () => [this.props.message.reactions]
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
