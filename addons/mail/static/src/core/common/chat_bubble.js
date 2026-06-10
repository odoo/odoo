import { useRef, useSubEnv } from "@web/owl2/utils";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ThreadPreview } from "@mail/core/common/thread_preview";

import { Component, computed, signal, useEffect } from "@odoo/owl";

import { useChildRef, useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { CountryFlag } from "@mail/core/common/country_flag";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { CountryFlag, DiscussAvatar };
    static props = ["chatWindow"];
    static template = "mail.ChatBubble";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const popoverRef = useChildRef();
        this.isMobileOS = isMobileOS();
        this.isPopoverOpen = signal(false);
        this.popover = usePopover(ThreadPreview, {
            animation: false,
            onClose: () => this.isPopoverOpen.set(false),
            position: "left-middle",
            popoverClass:
                "dropdown-menu bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
            ref: popoverRef,
        });
        this.env.bus.addEventListener("ChatBubble:preview-will-open", ({ detail }) => {
            if (detail === this) {
                return;
            }
            this.popover.close();
        });
        this.hover = useHover(["root", popoverRef], {
            onHover: () => {
                this.env.bus.trigger("ChatBubble:preview-will-open", this);
                this.popover.open(this.rootRef.el, {
                    channel: this.channel,
                    className: "o-mail-ChatBubble-preview",
                });
                this.isPopoverOpen.set(true);
            },
            onAway: () => this.popover.close(),
        });
        this.rootRef = useRef("root");
        this.bouncing = signal(false);
        const isImportant = computed(() => Boolean(this.channel?.importantCounter));
        useEffect(() => this.bouncing.set(isImportant));
        useSubEnv({ inChatBubble: true });
    }

    /** @returns {import("models").Channel} */
    get channel() {
        return this.props.chatWindow.channel;
    }
}
