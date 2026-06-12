import { useLayoutEffect } from "@web/owl2/utils";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component, onMounted, props, t, useListener } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { emojiLoader, useLoadEmoji } from "@web/core/emoji_picker/emoji_loader";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { TabHeader, TabPanel, Tabs } from "./tabs";

export class MessageReactionMenu extends Component {
    static components = { Dialog, Tabs, TabHeader, TabPanel };
    static template = "mail.MessageReactionMenu";

    setup() {
        super.setup();
        this.tabsRef = useChildRef();
        this.store = useService("mail.store");
        this.props = props({
            close: t.function([]),
            initialReaction: t.instanceOf(this.store.MessageReactions.Class).optional(),
            message: t.instanceOf(this.store["mail.message"].Class),
        });
        this.ui = useService("ui");
        useLayoutEffect(
            (closeFn) => {
                closeFn?.();
            },
            () => [this.props.message.reactions.length === 0 ? this.props.close : null]
        );
        useListener(document, "keydown", (ev) => this.onKeydown(ev));
        onExternalClick(this.tabsRef, () => this.props.close());
        onMounted(useLoadEmoji());
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
        return emojiLoader.getShortCode(reaction.content);
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
