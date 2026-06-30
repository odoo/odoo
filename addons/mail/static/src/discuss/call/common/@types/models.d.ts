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
        activeRtcSession: RtcSession;
        cancelRtcInvitationTimeout: number|undefined;
        focusAvailableVideo: () => void;
        focusStack: RtcSession[];
        hadSelfSession: boolean;
        hasRtcSessionActive: Readonly<boolean>;
        isCallDisplayedInChatWindow: Readonly<boolean>;
        isSelfInCall: Readonly<boolean>;
        lastSessionIds: Set<number>;
        pin: (session: RtcSession) => void;
        pinnedRtcSession: RtcSession;
        promoteFullscreen: typeof CALL_PROMOTE_FULLSCREEN[keyof CALL_PROMOTE_FULLSCREEN];
        rtc_session_ids: RtcSession[];
        showCallView: Readonly<boolean>;
        unpin: () => void;
        updateCallFocusStack: (session: RtcSession) => void;
        useCameraByDefault: null;
        videoCount: number;
        videoCountNotSelf: number;
        visibleCards: import("@mail/discuss/call/common/call").CardData[];
    }
    export interface MailGuest {
        currentRtcSession: RtcSession;
    }
    export interface ResPartner {
        currentRtcSession: RtcSession;
    }
    export interface Settings {
        getVolume: (rtcSession: RtcSession) => number;
    }
    export interface Store {
        _hasFullscreenUrl: boolean;
        _hasFullscreenUrlOnUpdate: () => void;
        _shareUrl: undefined|unknown;
        allActiveRtcSessions: RtcSession[];
        "discuss.channel.rtc.session": StaticMailRecord<RtcSession, typeof RtcSessionClass>;
        fullscreenChannel: DiscussChannel;
        meetingViewOpened: boolean;
        nextTalkingTime: number;
        ringingChannels: DiscussChannel[];
        rtc: Rtc;
        Rtc: StaticMailRecord<Rtc, typeof RtcClass>;
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession;
        Rtc: Rtc;
    }
}
