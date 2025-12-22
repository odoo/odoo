import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread_model";
import { callActionsRegistry } from "../common/call_actions";
import { useHover } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallParticipants extends Component {
    static template = "mail.DiscussSidebarCallParticipants";
    static props = { thread: { type: Thread }, compact: { type: Boolean, optional: true } };
    static components = { DiscussSidebarCallParticipants, Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.hover = useHover(["root", "floating*"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.floating = useDropdownState();
    }

    get callActionsRegistry() {
        return callActionsRegistry;
    }

    get compact() {
        if (typeof this.props.compact === "boolean") {
            return this.props.compact;
        }
        return this.store.discuss.isSidebarCompact;
    }

    get lastActiveSession() {
        const sessions = [...this.props.thread.rtcSessions];
        sessions?.sort((s1, s2) => {
            if (s1.isActuallyTalking && !s2.isActuallyTalking) {
                return -1;
            }
            if (!s1.isActuallyTalking && s2.isActuallyTalking) {
                return 1;
            }
            if (s1.isVideoStreaming && !s2.isVideoStreaming) {
                return -1;
            }
            if (!s1.isVideoStreaming && s2.isVideoStreaming) {
                return 1;
            }
            return s2.talkingTime - s1.talkingTime;
        });
        return sessions[0];
    }

    get sessions() {
        const sessions = [...this.props.thread.rtcSessions];
        return sessions.sort((s1, s2) => {
            const persona1 = s1.channelMember?.persona;
            const persona2 = s2.channelMember?.persona;
            return (
                persona1?.name?.localeCompare(persona2?.name) ||
                s1.channelMember?.id - s2.channelMember?.id ||
                s1.id - s2.id
            );
        });
    }
}
