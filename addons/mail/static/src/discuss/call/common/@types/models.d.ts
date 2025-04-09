declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}

    export interface ChannelMember {
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
        rtcInvitingSession: RtcSession;
        rtc_session_ids: RtcSession[];
        videoCount: Readonly<number>;
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession;
        Rtc: Rtc;
    }
}
