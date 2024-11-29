declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface ChannelMember {
        rtcSession: RtcSession,
    }
    export interface Store {
        allActiveRtcSessions: RtcSession[],
        ["discuss.channel.rtc.session"]: typeof RtcSessionClass,
        nextTalkingTime: number,
        ringingThreads: Thread[],
    }
    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}
    export interface Thread {
        activeRtcSession: RtcSession,
        rtcInvitingSession: RtcSession,
        rtcSessions: RtcSession[],
    }

    export interface Models {
        "discuss.channel.rtc.session": RtcSession,
    }
}
