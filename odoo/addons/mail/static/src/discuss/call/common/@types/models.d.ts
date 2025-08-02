declare module "models" {
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";

    export interface DiscussApp {
        ringingThreads: Thread[],
    }
    export interface RtcSession extends RtcSessionClass {}

    export interface Models {
        "RtcSession": RtcSession,
    }
}
