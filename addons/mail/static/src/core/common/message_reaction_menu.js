/* @odoo-module */

import { loadEmoji } from "@mail/core/common/emoji_picker";
import { useStore } from "@mail/core/common/messaging_hook";
import { avatarUrl } from "@mail/core/common/thread_service";
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
import { removeReaction } from "./message_service";

export class MessageReactionMenu extends Component {
    static props = ["close", "message"];
    static components = { Dialog };
    static template = "mail.MessageReactionMenu";

    setup() {
        this.root = useRef("root");
        this.store = useStore();
        this.ui = useState(useService("ui"));
        this.avatarUrl = avatarUrl;
        this.state = useState({
            reaction: this.props.message.reactions[0],
        });
        this.removeReaction = removeReaction;
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
