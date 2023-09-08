/* add this file in jsconfig.json, in typeRoots array */
declare module "models" {
    import { Attachment } from "@mail/core/common/attachment_model";
    import { Composer } from "@mail/core/common/composer_model";
    import { Follower } from "@mail/core/common/follower_model";
    import { Message } from "@mail/core/common/message_model";
    import { Persona } from "@mail/core/common/persona_model";
    import { RtcSession } from "@mail/discuss/call/common/rtc_session_model";
    import { Thread } from "@mail/core/common/thread_model";

    export interface Models {
        "Attachment": Attachment,
        "Composer": Composer,
        "Follower": Follower,
        "Message": Message,
        "Persona": Persona,
        "RtcSession": RtcSession,
        "Thread": Thread,
    }
}
