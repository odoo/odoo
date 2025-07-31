declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}

    export interface ChannelMember {
        rtc_inviting_session_id: RtcSession;
        rtcSession: RtcSession;
    }
    export interface Persona {
        currentRtcSession: RtcSession;
    }
    export interface Settings {
        getVolume: (rtcSession: RtcSession) => number;
    }
    export interface Store {
        allActiveRtcSessions: RtcSession[];
        "discuss.channel.rtc.session": StaticMailRecord<RtcSession, typeof RtcSessionClass>;
        nextTalkingTime: number;
        ringingThreads: Thread[];
        rtc: Rtc;
        Rtc: StaticMailRecord<Rtc, typeof RtcClass>;
    }
    export interface Thread {
        activeRtcSession: RtcSession;
        cancelRtcInvitationTimeout: number|undefined;
        hadSelfSession: boolean;
        lastSessionIds: Set<number>;
        promoteFullscreen: typeof CALL_PROMOTE_FULLSCREEN[keyof CALL_PROMOTE_FULLSCREEN];
        rtc_session_ids: RtcSession[];
        videoCount: number;
        videoCountNotSelf: number;
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession;
        Rtc: Rtc;
    }
}
