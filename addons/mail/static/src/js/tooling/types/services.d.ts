/* add this file in jsconfig.json, in typeRoots array */
declare module "services" {
    import { attachmentUploadService } from "@mail/core/common/attachment_upload_service";
    import { discussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
    import { discussCorePublic } from "@mail/discuss/core/public/discuss_core_public_service";
    import { discussCoreWeb } from "@mail/discuss/core/web/discuss_core_web_service";
    import { discussTypingService } from "@mail/discuss/typing/common/typing_service"
    import { mailCoreCommon } from "@mail/core/common/mail_core_common_service";
    import { mailCoreWeb } from "@mail/core/web/mail_core_web_service";
    import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
    import { outOfFocusService } from "@mail/core/common/out_of_focus_service";
    import { discussP2P } from "@mail/discuss/call/common/discuss_p2p_service";
    import { rtcService } from "@mail/discuss/call/common/rtc_service";
    import { soundEffects } from "@mail/core/common/sound_effects_service";
    import { storeService } from "@mail/core/common/store_service";
    import { suggestionService } from "@mail/core/common/suggestion_service";

    export interface Services {
        "discuss.core.common": typeof discussCoreCommon;
        "discuss.core.public": typeof discussCorePublic;
        "discuss.core.web": typeof discussCoreWeb;
        "discuss.p2p": typeof discussP2P;
        "discuss.rtc": typeof rtcService;
        "discuss.typing": typeof discussTypingService;
        "mail.attachment_upload": typeof attachmentUploadService;
        "mail.core.common": typeof mailCoreCommon;
        "mail.core.web": typeof mailCoreWeb;
        "mail.notification.permission": typeof notificationPermissionService;
        "mail.out_of_focus": typeof outOfFocusService;
        "mail.sound_effects": typeof soundEffects;
        "mail.store": typeof storeService;
        "mail.suggestion": typeof suggestionService;
    }
}
