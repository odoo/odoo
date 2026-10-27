import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { useThreadPreview } from "@mail/core/common/thread_preview";

import { Component, computed, signal, types, useEffect, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { CountryFlag } from "@mail/core/common/country_flag";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { isMobileOS } from "@web/core/browser/feature_detection";

/** Minimum time the bubble keeps bouncing after important messages, in ms. */
export const BOUNCE_DURATION = 4000;

export class ChatBubble extends Component {
    static components = { CountryFlag, DiscussAvatar };
    static template = "mail.ChatBubble";

    rootRef = signal.ref();

    setup() {
        super.setup();
        this.ancestors = useAncestors({ inChatBubble: true });
        this.store = useService("mail.store");
        this.props = useProps({
            chatWindow: types.instanceOf(this.store.ChatWindow),
        });
        this.isMobileOS = isMobileOS();
        this.threadPreview = useThreadPreview(this.rootRef, {
            channel: () => this.channel,
            className: "o-mail-ChatBubble-preview",
            position: "left-middle",
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
