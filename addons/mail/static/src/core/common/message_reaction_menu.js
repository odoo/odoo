import { onExternalClick } from "@mail/utils/common/hooks";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

import { Component, onMounted, useExternalListener } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { TabHeader, TabPanel, Tabs } from "./tabs";

export class MessageReactionMenu extends Component {
    static props = ["close", "message", "initialReaction?"];
    static components = { Dialog, Tabs, TabHeader, TabPanel };
    static template = "mail.MessageReactionMenu";

    setup() {
        super.setup();
        this.tabsRef = useChildRef();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useExternalListener(document, "keydown", this.onKeydown);
        onExternalClick(this.tabsRef, () => this.props.close());
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
        return (
            this.store.emojiLoader.loaded?.emojiValueToShortcodes?.[reaction.content]?.[0] ?? "?"
        );
    }

    get contentClass() {
        const attClass = {
            "o-mail-MessageReactionMenu h-50 d-flex": true,
            "position-absolute bottom-0 start-0": this.store.useMobileView,
        };
        return Object.entries(attClass)
            .filter(([classNames, value]) => value)
            .map(([classNames]) => classNames)
            .join(" ");
    }
}
