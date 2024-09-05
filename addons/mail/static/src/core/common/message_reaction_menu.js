import { loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";
import { onExternalClick } from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    onPatched,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionMenu extends Component {
    static props = ["close", "message", "initialReaction?"];
    static components = { Dialog };
    static template = "mail.MessageReactionMenu";

    setup() {
        super.setup();
        this.root = useRef("root");
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.state = useState({
            emojiLoaded: Boolean(loader.loaded),
            reaction: this.props.initialReaction
                ? this.props.initialReaction
                : this.props.message.reactions[0],
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
        onMounted(async () => {
            if (!loader.loaded) {
                loadEmoji();
            }
        });
        if (!loader.loaded) {
            loader.onEmojiLoaded(() => (this.state.emojiLoaded = true));
        }
        onMounted(() => void this.state.emojiLoaded);
        onPatched(() => void this.state.emojiLoaded);
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
        return loader.loaded?.emojiValueToShortcode?.[reaction.content] ?? "?";
    }
}
