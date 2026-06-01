import { Component, signal, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CALL_ICON_DEAFEN, CALL_ICON_MUTED } from "@mail/discuss/call/common/call_actions";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { useHover } from "@mail/utils/common/hooks";
import { toggleFn } from "@mail/utils/common/signal";

import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { localeCompare } from "@web/core/l10n/utils";

/**
 * @typedef {Object} Props
 * @property {import("models").DiscussChannel} channel
 * @property {Boolean|undefined} [compact]
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallParticipants extends Component {
    static template = "mail.DiscussSidebarCallParticipants";
    static props = ["channel", "compact?"];
    static components = { AvatarStack, DiscussSidebarCallParticipants, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.hover = useHover(["root", "floating"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.expanded = signal(false);
        this.floating = useDropdownState();
        this.toggleFn = toggleFn;
        this.CALL_ICON_DEAFEN = CALL_ICON_DEAFEN;
        this.CALL_ICON_MUTED = CALL_ICON_MUTED;
        useEffect(() => {
            if (this.rtc.selfSession?.in(this.sessions) && !this.compact) {
                this.expanded.set(true);
            }
            if (this.compact) {
                this.expanded.set(false);
            }
        });
    }

    get compact() {
        if (typeof this.props.compact === "boolean") {
            return this.props.compact;
        }
        return this.store.discuss.isSidebarCompact;
    }

    get lastActiveSession() {
        const sessions = [...this.props.channel.rtc_session_ids];
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

    attClass(session) {
        return {
            "justify-content-center bg-inherit": this.compact,
        };
    }

    get sessions() {
        const sessions = [...this.props.channel.rtc_session_ids];
        return sessions.sort((s1, s2) => {
            const member1 = s1.channel_member_id;
            const member2 = s2.channel_member_id;
            const name1 = member1?.persona?.displayName;
            const name2 = member2?.persona?.displayName;
            const nameDiff = localeCompare(name1, name2);
            if (nameDiff !== 0) {
                return nameDiff;
            }
            if (member1?.id && !member2?.id) {
                return -1;
            }
            if (!member1?.id && member2?.id) {
                return 1;
            }
            const memberDiff = member1?.id - member2?.id;
            if (memberDiff !== 0) {
                return memberDiff;
            }
            return s1.id - s2.id;
        });
    }

    /**
     * @param {import("models").Persona} persona
     */
    avatarClass(persona) {
        return persona.currentRtcSession?.isActuallyTalking
            ? "o-mail-DiscussSidebarCallParticipants-avatar o-isTalking"
            : "";
    }

    onClickAvatarStack() {
        if (this.compact) {
            return;
        }
        this.expanded.set(true);
    }

    get title() {
        return this.expanded() ? _t("Collapse participants") : _t("Expand participants");
    }

    onClickParticipant(ev, session) {}
}
