declare module "models" {
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface Store {
        ringingThreads: Thread[],
        nextTalkingTime: number,
    }
    export interface Rtc extends RtcClass {}
    export interface RtcSession extends RtcSessionClass {}
    export interface Thread {
        rtcSessions: RtcSession[],
    }

    export interface Models {
        "RtcSession": RtcSession,
    }
}
