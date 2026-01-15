/* add this file in jsconfig.json, in typeRoots array */
declare module "services" {
    import { attachmentUploadService } from "@mail/core/common/attachment_upload_service";
    import { discussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
    import { discussCorePublic } from "@mail/discuss/core/public/discuss_core_public_service";
    import { discussCorePublicWeb } from "@mail/discuss/core/public_web/discuss_core_public_web_service";
    import { discussCoreWeb } from "@mail/discuss/core/web/discuss_core_web_service";
    import { im_status } from "@mail/core/common/im_status_service";
    import { mailCoreCommon } from "@mail/core/common/mail_core_common_service";
    import { mailCoreWeb } from "@mail/core/web/mail_core_web_service";
    import { mailPopoutService } from "@mail/core/common/mail_popout_service";
    import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
    import { outOfFocusService } from "@mail/core/common/out_of_focus_service";
    import { discussP2P } from "@mail/discuss/call/common/discuss_p2p_service";
    import { pttExtensionHookService } from "@mail/discuss/call/common/ptt_extension_service";
    import { rtcService } from "@mail/discuss/call/common/rtc_service";
    import { soundEffects } from "@mail/core/common/sound_effects_service";
    import { storeService } from "@mail/core/common/store_service";
    import { suggestionService } from "@mail/core/common/suggestion_service";
    import { voiceMessageService } from "@mail/discuss/voice_message/common/voice_message_service";

    export interface Services {
        "discuss.core.common": typeof discussCoreCommon;
        "discuss.core.public": typeof discussCorePublic;
        "discuss.core.public.web": typeof discussCorePublicWeb;
        "discuss.core.web": typeof discussCoreWeb;
        "discuss.p2p": typeof discussP2P;
        "discuss.ptt_extension": typeof pttExtensionHookService;
        "discuss.rtc": typeof rtcService;
        "discuss.voice_message": typeof voiceMessageService;
        "mail.attachment_upload": typeof attachmentUploadService;
        "mail.core.common": typeof mailCoreCommon;
        "mail.core.web": typeof mailCoreWeb;
        "mail.notification.permission": typeof notificationPermissionService;
        "mail.out_of_focus": typeof outOfFocusService;
        "mail.popout": typeof mailPopoutService;
        "mail.sound_effects": typeof soundEffects;
        "mail.store": typeof storeService;
        "mail.suggestion": typeof suggestionService;
        im_status: typeof im_status;
    }
}
