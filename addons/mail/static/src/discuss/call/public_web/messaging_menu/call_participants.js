import { CALL_ICON_DEAFEN, CALL_ICON_MUTED } from "@mail/discuss/call/common/call_actions";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { toggleFn } from "@mail/utils/common/signal";

import { Component, computed, props, signal, t, useEffect } from "@odoo/owl";

import { localeCompare } from "@web/core/l10n/utils/collation";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuCallParticipants extends Component {
    static template = "mail.MessagingMenuCallParticipants";
    static components = { AvatarStack };

    CALL_ICON_DEAFEN = CALL_ICON_DEAFEN;
    CALL_ICON_MUTED = CALL_ICON_MUTED;
    toggleFn = toggleFn;
    expanded = signal(false);
    personas = computed(() =>
        this.sessions.map((session) => session.channel_member_id?.persona).filter(Boolean)
    );
    selfInCall = computed(() => Boolean(this.rtc.selfSession?.in(this.channel.rtc_session_ids)));

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.channel = props.static("channel", t.instanceOf(this.store["discuss.channel"].Class));
        useEffect(() => {
            this.expanded.set(this.selfInCall());
        });
    }

    get sessions() {
        const sessions = [...this.channel.rtc_session_ids];
        return sessions.sort((s1, s2) => {
            const nameDiff = localeCompare(s1.name, s2.name);
            if (nameDiff !== 0) {
                return nameDiff;
            }
            return s1.id - s2.id;
        });
    }

    get title() {
        return this.expanded() ? _t("Collapse participants") : _t("Expand participants");
    }

    /** @param {import("models").Persona} persona */
    avatarClass(persona) {
        return { "o-isTalking": persona.currentRtcSession?.isActuallyTalking };
    }

    onClickAvatarStack(ev) {
        ev.stopPropagation();
        this.expanded.set(true);
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").RtcSession} session
     */
    onClickParticipant(ev, session) {}

    /** @param {import("models").RtcSession} session */
    participantClass(session) {
        return {};
    }
}
