declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}

    export interface ChannelMember {
        cancelInvitationTimeout: () => void;
        rtc_inviting_session_id: RtcSession;
        rtcSession: RtcSession;
        startInvitationTimeout: () => void;
    }
    export interface DiscussChannel {
        _playRtcSessionsSoundEffects: (rtcSessions: RtcSession[]) => Promise<void>;
        activeRtcSession: RtcSession;
        activeSpeakers: RtcSession[];
        cancelRtcInvitationTimeout: number|undefined;
        clearActiveSpeakers: () => void;
        focusAvailableVideo: () => void;
        focusStack: RtcSession[];
        hadSelfSession: boolean;
        hasRtcSessionActive: Readonly<boolean>;
        isCallDisplayedInChatWindow: Readonly<boolean>;
        isSelfInCall: Readonly<boolean>;
        lastSessionIds: Set<number>;
        pin: (session: RtcSession) => void;
        pinnedRtcSession: RtcSession;
        pruneSpeakersTimeout: number|undefined;
        rtc_session_ids: RtcSession[];
        showCallView: Readonly<boolean>;
        unpin: () => void;
        updateActiveSpeakers: () => void;
        updateCallFocusStack: (session: RtcSession) => void;
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
        _hasFullscreenUrlOnUpdate: (hasFullscreenUrl: boolean) => void;
        "discuss.channel.rtc.session": StaticMailRecord<RtcSession, typeof RtcSessionClass>;
        fullscreenChannel: DiscussChannel;
        meetingViewOpened: boolean;
        nextTalkingTime: number;
        ringingChannels: DiscussChannel[];
        rtc: Rtc;
        Rtc: StaticMailRecord<Rtc, typeof RtcClass>;
        shareUrl: Readonly<string|undefined>;
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession;
        Rtc: Rtc;
    }
}
