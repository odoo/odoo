/* @odoo-module */

import { createLocalId } from "../utils/misc";

export class Channel {
    /** @type {number} */
    id;
    // /** @type {string} */
    // type;
    /** @type {import("@mail/core/store_service").Store} */
    _store;
    /** @type {import("@mail/discuss/discuss_store_service").Discusstore} */
    discussStore;
    /** @type {integer} */
    activeRtcSessionId;
    /** @type {RtcSession{}} */
    rtcSessions = {};
    invitingRtcSessionId;
    /** @type {Set<number>} */
    invitedMemberIds = new Set();
    /** @type {import("@mail/discuss/channel_member_model").ChannelMember[]} */
    channelMembers = [];
    /** @type {integer} */
    memberCount = 0;

    get localId() {
        return createLocalId(this.model, this.id);
    }

    get activeRtcSession() {
        return this.discussStore.rtcSessions[this.activeRtcSessionId];
    }

    set activeRtcSession(session) {
        this.activeRtcSessionId = session?.id;
    }

    get onlineMembers() {
        const orderedOnlineMembers = [];
        for (const member of this.channelMembers) {
            if (member.persona.im_status === "online") {
                orderedOnlineMembers.push(member);
            }
        }
        return orderedOnlineMembers.sort((m1, m2) => {
            const m1HasRtc = Boolean(m1.rtcSession);
            const m2HasRtc = Boolean(m2.rtcSession);
            if (m1HasRtc === m2HasRtc) {
                /**
                 * If raisingHand is falsy, it gets an Infinity value so that when
                 * we sort by [oldest/lowest-value]-first, falsy values end up last.
                 */
                const m1RaisingValue = m1.rtcSession?.raisingHand || Infinity;
                const m2RaisingValue = m2.rtcSession?.raisingHand || Infinity;
                if (m1HasRtc && m1RaisingValue !== m2RaisingValue) {
                    return m1RaisingValue - m2RaisingValue;
                } else {
                    return m1.persona.name?.localeCompare(m2.persona.name) ?? 1;
                }
            } else {
                return m2HasRtc - m1HasRtc;
            }
        });
    }

    get offlineMembers() {
        const orderedOnlineMembers = [];
        for (const member of this.channelMembers) {
            if (member.persona.im_status !== "online") {
                orderedOnlineMembers.push(member);
            }
        }
        return orderedOnlineMembers.sort((m1, m2) => (m1.persona.name < m2.persona.name ? -1 : 1));
    }

    get unknownMembersCount() {
        return this.memberCount - this.channelMembers.length;
    }

    get rtcInvitingSession() {
        return this.discussStore.rtcSessions[this.invitingRtcSessionId];
    }

    get videoCount() {
        return Object.values(this.rtcSessions).filter((session) => session.videoStream).length;
    }

    get areAllMembersLoaded() {
        return this.memberCount === this.channelMembers.length;
    }

    /** @type {import("@mail/core/persona_model").Persona|undefined} */
    get correspondent() {
        if (this.type === "channel") {
            return undefined;
        }
        const correspondents = this.channelMembers
            .map((member) => member.persona)
            .filter((persona) => !!persona)
            .filter(
                ({ id, type }) =>
                    id !== (type === "partner" ? this._store.user?.id : this._store.guest?.id)
            );
        if (correspondents.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents.length === 0 && this.channelMembers.length === 1) {
            // Self-chat.
            return this._store.user;
        }
        return undefined;
    }

    get hasSelfAsMember() {
        return this.channelMembers.some(
            (channelMember) => channelMember.persona === this._store.self
        );
    }

    get allowCalls() {
        return (
            ["chat", "channel", "group"].includes(this.type) &&
            this.correspondent !== this._store.odoobot
        );
    }

    get hasMemberList() {
        return ["channel", "group"].includes(this.type);
    }
}
