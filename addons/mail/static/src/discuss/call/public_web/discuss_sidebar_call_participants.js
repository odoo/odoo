import { Component, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread_model";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { callActionsRegistry } from "../common/call_actions";
import { useHover } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallParticipants extends Component {
    static template = "mail.DiscussSidebarCallParticipants";
    static props = { thread: { type: Thread }, compact: { type: Boolean, optional: true } };
    static components = { AvatarStack, DiscussSidebarCallParticipants, Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.hover = useHover(["root", "floating*"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.state = useState({ expanded: false });
        this.floating = useDropdownState();
        useEffect(
            (selfSession, compact) => {
                if (selfSession?.in(this.sessions) && !compact) {
                    this.state.expanded = true;
                }
                if (compact) {
                    this.state.expanded = false;
                }
            },
            () => [this.rtc.selfSession, this.compact]
        );
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
            return (
                s1.channel_member_id?.persona?.nameOrDisplayName?.localeCompare(
                    s2.channel_member_id?.persona?.nameOrDisplayName
                ) ?? 1
            );
        });
    }

    /**
     * @param {import("models").Persona} persona
     */
    avatarClass(persona) {
        return this.state.expanded && persona.currentRtcSession?.isActuallyTalking
            ? "o-mail-DiscussSidebarCallParticipants-avatar o-isTalking"
            : "";
    }

    get title() {
        return this.state.expanded ? _t("Collapse") : _t("Expand");
    }
}
