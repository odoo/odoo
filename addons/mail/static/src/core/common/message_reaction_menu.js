import { TabHeader, TabPanel, Tabs } from "@mail/core/common/tabs";
import { useDialogCloseOnClickAway } from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    signal,
    t,
    untrack,
    useEffect,
    useListener,
    useProps,
} from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { emojiLoader, useLoadEmoji } from "@web/core/emoji_picker/emoji_loader";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionMenu extends Component {
    static components = { Dialog, Tabs, TabHeader, TabPanel };
    static template = "mail.MessageReactionMenu";

    setup() {
        super.setup();
        this.modalRef = signal.ref();
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]),
            initialReaction: t.instanceOf(this.store.MessageReactions).optional(),
            message: t.instanceOf(this.store["mail.message"]),
        });
        this.ui = useService("ui");
        useEffect(() => {
            const closeFn = this.props.message.reactions.length === 0 ? this.props.close : null;
            untrack(() => closeFn?.());
        });
        useListener(document, "keydown", (ev) => this.onKeydown(ev));
        useDialogCloseOnClickAway(this.modalRef, () => this.props.close());
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
