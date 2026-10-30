import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";
import { useHover } from "@mail/utils/common/hooks";

import { Component, onWillUnmount, signal, types, useListener, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";

export class ThreadPreview extends Component {
    static components = { MessageSeenIndicator };
    static template = "mail.ThreadPreview";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            channel: types.instanceOf(this.store["discuss.channel"]),
            className: types.string().optional(""),
        });
    }

    attClass() {
        const bubbleColor = this.lastMessage()?.bubbleColor;
        return {
            [this.props.className]: true,
            "o-blue": bubbleColor === "blue",
            "o-green": bubbleColor === "green",
            "o-orange": bubbleColor === "orange",
        };
    }

    lastMessage() {
        return this.props.channel.newestPersistentOfAllMessage;
    }

    previewText() {
        return this.lastMessage()?.previewText || _t("This is the start of your conversation");
    }
}

/** Shows the preview of a channel next to the root while hovered, one preview at a time. */
export function useThreadPreview(
    rootRef,
    { canOpen = () => true, channel, className, delay = 0, position }
) {
    const env = useEnv();
    const isOpen = signal(false);
    const popover = usePopover(ThreadPreview, {
        animation: false,
        onClose: () => isOpen.set(false),
        popoverClass:
            "o-mail-ThreadPreview-popover bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
        position,
        setActiveElement: false,
    });
    /** Whether the pointer on the root is a mouse: a touch tap does not count as hovering. */
    let isMouse = false;
    let timeout;
    const open = () => {
        if (!isMouse || !hover.isHover || !canOpen()) {
            return;
        }
        env.bus.trigger("ThreadPreview:will-open", popover);
        popover.open(rootRef(), { channel: channel(), className });
        isOpen.set(true);
    };
    const close = () => {
        clearTimeout(timeout);
        popover.close();
    };
    useListener(env.bus, "ThreadPreview:will-open", ({ detail }) => {
        if (detail !== popover) {
            close();
        }
    });
    useListener(rootRef, "pointerenter", (ev) => (isMouse = ev.pointerType === "mouse"));
    const hover = useHover(rootRef, {
        onHover: () => {
            clearTimeout(timeout);
            if (delay) {
                timeout = setTimeout(open, delay);
            } else {
                open();
            }
        },
        onAway: close,
    });
    onWillUnmount(() => clearTimeout(timeout));
    return { close, isOpen };
}
