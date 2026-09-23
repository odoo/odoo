// @ts-check
/** @odoo-module native */
import { Thread } from "@mail/core/common/thread_model";
import {
    CALL_ICON_DEAFEN,
    CALL_ICON_MUTED,
} from "@mail/discuss/call/common/call_actions";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { useHover } from "@mail/utils/common/hooks";
import { Component, onWillRender, useEffect, useState } from "@odoo/owl";
import { Dropdown, useDropdownState } from "@web/components/dropdown";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {boolean} [compact]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class DiscussSidebarCallParticipants extends Component {
    static template = "mail.DiscussSidebarCallParticipants";
    static props = {
        thread: { type: Thread },
        compact: { type: Boolean, optional: true },
    };
    static components = { AvatarStack, DiscussSidebarCallParticipants, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.hover = useHover(["root", "floating"], {
            onHover: () => (this.floating.isOpen = true),
            onAway: () => (this.floating.isOpen = false),
        });
        this.state = useState({ expanded: false });
        this.floating = useDropdownState();
        this.CALL_ICON_DEAFEN = CALL_ICON_DEAFEN;
        this.CALL_ICON_MUTED = CALL_ICON_MUTED;
        /** @type {import("models").RtcSession[]} */
        this.sessions = [];
        onWillRender(() => this.computeSessions());
        useEffect(
            /**
             * @param {import("models").RtcSession|undefined} selfSession
             * @param {boolean} compact
             */
            (selfSession, compact) => {
                if (selfSession?.in(this.sessions) && !compact) {
                    this.state.expanded = true;
                }
                if (compact) {
                    this.state.expanded = false;
                }
            },
            () => [this.rtc.selfSession, this.compact],
        );
    }

    get compact() {
        if (typeof this.props.compact === "boolean") {
            return this.props.compact;
        }
        return this.store.discuss.isSidebarCompact;
    }

    /** @param {import("models").RtcSession} session */
    participantClass(session) {
        return {
            "justify-content-center bg-inherit": this.compact,
        };
    }

    computeSessions() {
        const sessions = [...this.props.thread.rtc_session_ids];
        this.sessions = sessions.sort((s1, s2) => {
            const persona1 = s1.channel_member_id?.persona;
            const persona2 = s2.channel_member_id?.persona;
            return (
                persona1?.name?.localeCompare(persona2?.name) ||
                s1.channel_member_id?.id - s2.channel_member_id?.id ||
                s1.id - s2.id
            );
        });
    }

    /** @param {import("models").Persona} persona */
    avatarClass(persona) {
        return persona.currentRtcSession?.isActuallyTalking
            ? "o-mail-DiscussSidebarCallParticipants-avatar o-isTalking"
            : "";
    }

    onClickAvatarStack() {
        if (this.compact) {
            return;
        }
        this.state.expanded = true;
    }

    get title() {
        return this.state.expanded
            ? _t("Collapse participants")
            : _t("Expand participants");
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").RtcSession} session
     */
    onClickParticipant(ev, session) {}
}
