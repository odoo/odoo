import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component, onMounted, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionMenu extends Component {
    static props = ["close", "message", "initialReaction?"];
    static components = { Dialog };
    static template = "mail.MessageReactionMenu";

    setup() {
        super.setup();
        this.root = useRef("root");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.state = useState({
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
        onMounted(() => {
            if (!this.store.emojiLoader.loaded) {
                loadEmoji();
            }
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
        return this.store.emojiLoader.loaded?.emojiValueToShortcodes?.[reaction.content][0] ?? "?";
    }

    get contentClass() {
        const attClass = {
            "o-mail-MessageReactionMenu h-50 d-flex": true,
            "position-absolute bottom-0": this.store.useMobileView,
        };
        return Object.entries(attClass)
            .filter(([classNames, value]) => value)
            .map(([classNames]) => classNames)
            .join(" ");
    }
}
