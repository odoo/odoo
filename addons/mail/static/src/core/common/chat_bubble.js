import { useSubEnv } from "@web/owl2/utils";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";

import { Component, computed, signal, types, useEffect, useListener, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { CountryFlag } from "@mail/core/common/country_flag";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

/** Minimum time the bubble keeps bouncing after important messages, in ms. */
export const BOUNCE_DURATION = 4000;

class ChatBubblePreview extends Component {
    static components = { MessageSeenIndicator };
    static template = "mail.ChatBubblePreview";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            chatWindow: types.instanceOf(this.store.ChatWindow),
        });
    }

    /** @returns {import("models").DiscussChannel} */
    get channel() {
        return this.props.chatWindow.channel;
    }

    get lastMessage() {
        return this.channel.newestPersistentOfAllMessage;
    }

    get previewText() {
        return this.lastMessage?.previewText || _t("This is the start of your conversation");
    }
}

export class ChatBubble extends Component {
    static components = { CountryFlag, DiscussAvatar };
    static template = "mail.ChatBubble";

    rootRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            chatWindow: types.instanceOf(this.store.ChatWindow),
        });
        const popoverRef = signal.ref();
        this.isMobileOS = isMobileOS();
        this.isPopoverOpen = signal(false);
        this.popover = usePopover(ChatBubblePreview, {
            animation: false,
            onClose: () => this.isPopoverOpen.set(false),
            position: "left-middle",
            popoverClass:
                "dropdown-menu bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
            ref: popoverRef,
        });
        useListener(this.env.bus, "ChatBubble:preview-will-open", ({ detail }) => {
            if (detail === this) {
                return;
            }
            this.popover.close();
        });
        this.hover = useHover([this.rootRef, popoverRef], {
            onHover: () => {
                this.env.bus.trigger("ChatBubble:preview-will-open", this);
                this.popover.open(this.rootRef(), { chatWindow: this.props.chatWindow });
                this.isPopoverOpen.set(true);
            },
            onAway: () => this.popover.close(),
        });
        this.bouncing = signal(false);
        const importantCounter = computed(() => this.channel?.importantCounter ?? 0);
        // Bounce only when new important messages come in, not on mount nor
        // when the counter merely goes down (e.g. messages being read).
        let previousCounter = importantCounter();
        useEffect(() => {
            const counter = importantCounter();
            if (counter > previousCounter) {
                this.startBouncing();
            } else if (counter === 0) {
                this.bouncing.set(false);
            }
            previousCounter = counter;
        });
        useSubEnv({ inChatBubble: true });
    }

    /** @returns {import("models").Channel} */
    get channel() {
        return this.props.chatWindow.channel;
    }

    /** Bounces for at least BOUNCE_DURATION, without restarting the animation. */
    startBouncing() {
        this.bounceDeadline = Date.now() + BOUNCE_DURATION;
        this.bouncing.set(true);
    }

    /** Called at the end of each bounce, i.e. when the bubble is back down. */
    onBounceEnd() {
        if (Date.now() >= this.bounceDeadline) {
            this.bouncing.set(false);
        }
    }
}
