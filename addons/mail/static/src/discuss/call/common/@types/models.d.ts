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
        getVolume: (rtcSession: unknown) => boolean;
    }
    export interface Store {
        Rtc: Rtc;
        "discuss.channel.rtc.session": RtcSession;
        allActiveRtcSessions: RtcSession[];
        nextTalkingTime: number;
        ringingThreads: Thread[];
        rtc: Rtc;
    }
    export interface Thread {
        activeRtcSession: RtcSession;
        hadSelfSession: boolean;
        lastSessionIds: Set;
        rtcInvitingSession: RtcSession;
        rtcSessions: RtcSession[];
        videoCount: Readonly<number>;
    }

    export interface Models {
        Rtc: Rtc;
        "discuss.channel.rtc.session": RtcSession;
    }
}
