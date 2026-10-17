declare module "models" {
    export interface ChannelMember {
        rtc_inviting_session_id: RtcSession;
        rtcSession: RtcSession;
    }
    export interface DiscussChannel {
        activeRtcSession: RtcSession;
        activeSpeakers: RtcSession[];
        cancelRtcInvitationTimeout: number|undefined;
        focusStack: RtcSession[];
        hadSelfSession: boolean;
        lastSessionIds: Set<number>;
        pinnedRtcSession: RtcSession;
        pruneSpeakersTimeout: number|undefined;
        rtc_session_ids: RtcSession[];
        useCameraByDefault: null;
        videoCount: number;
        visibleCards: import("@mail/discuss/call/common/call").CardData[];
    }
    export interface MailGuest {
        currentRtcSession: RtcSession;
    }
    export interface ResPartner {
        currentRtcSession: RtcSession;
    }
    export interface Store {
        _hasFullscreenUrl: boolean;
        fullscreenChannel: DiscussChannel;
        meetingViewOpened: boolean;
        nextTalkingTime: number;
        ringingChannels: DiscussChannel[];
        rtc: Rtc;
    }
}
