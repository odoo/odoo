declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}

    export interface ChannelMember {
        rtc_inviting_session_id: RtcSession;
        rtcSession: RtcSession;
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
        allActiveRtcSessions: RtcSession[];
        "discuss.channel.rtc.session": StaticMailRecord<RtcSession, typeof RtcSessionClass>;
        fullscreenChannel: Thread;
        meetingViewOpened: boolean;
        nextTalkingTime: number;
        ringingThreads: Thread[];
        rtc: Rtc;
        Rtc: StaticMailRecord<Rtc, typeof RtcClass>;
    }
    export interface Thread {
        activeRtcSession: RtcSession;
        cancelRtcInvitationTimeout: number|undefined;
        focusAvailableVideo: () => void;
        focusStack: RtcSession[];
        hadSelfSession: boolean;
        isCallDisplayedInChatWindow: boolean;
        lastSessionIds: Set<number>;
        promoteFullscreen: typeof CALL_PROMOTE_FULLSCREEN[keyof CALL_PROMOTE_FULLSCREEN];
        rtc_session_ids: RtcSession[];
        showCallView: Readonly<boolean>;
        updateCallFocusStack: (session: RtcSession) => void;
        useCameraByDefault: null;
        videoCount: number;
        videoCountNotSelf: number;
        visibleCards: CardData[];
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession;
        Rtc: Rtc;
    }
}
