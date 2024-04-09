/* add this file in jsconfig.json, in typeRoots array */
declare module "services" {
    import { activityService } from "@mail/core/web/activity_service";
    import { attachmentService } from "@mail/core/common/attachment_service";
    import { attachmentUploadService } from "@mail/core/common/attachment_upload_service";
    import { channelMemberService } from "@mail/core/common/channel_member_service";
    import { chatWindowService } from "@mail/core/common/chat_window_service";
    import { discussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
    import { discussCorePublic } from "@mail/discuss/core/public/discuss_core_public_service";
    import { discussCoreWeb } from "@mail/discuss/core/web/discuss_core_web_service";
    import { discussTypingService } from "@mail/discuss/typing/common/typing_service"
    import { mailCoreCommon } from "@mail/core/common/mail_core_common_service";
    import { mailCoreWeb } from "@mail/core/web/mail_core_web_service";
    import { messageService } from "@mail/core/common/message_service";
    import { messagingService } from "@mail/core/common/messaging_service";
    import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
    import { outOfFocusService } from "@mail/core/common/out_of_focus_service";
    import { personaService } from "@mail/core/common/persona_service";
    import { rtcService } from "@mail/discuss/call/common/rtc_service";
    import { soundEffects } from "@mail/core/common/sound_effects_service";
    import { storeService } from "@mail/core/common/store_service";
    import { suggestionService } from "@mail/core/common/suggestion_service";

    export interface Services {
        "discuss.channel.member": typeof channelMemberService;
        "discuss.core.common": typeof discussCoreCommon;
        "discuss.core.public": typeof discussCorePublic;
        "discuss.core.web": typeof discussCoreWeb;
        "discuss.rtc": typeof rtcService;
        "discuss.typing": typeof discussTypingService;
        "mail.activity": typeof activityService;
        "mail.attachment": typeof attachmentService;
        "mail.attachment_upload": typeof attachmentUploadService;
        "mail.chat_window": typeof chatWindowService;
        "mail.core.common": typeof mailCoreCommon;
        "mail.core.web": typeof mailCoreWeb;
        "mail.message": typeof messageService;
        "mail.messaging": typeof messagingService;
        "mail.notification.permission": typeof notificationPermissionService;
        "mail.out_of_focus": typeof outOfFocusService;
        "mail.persona": typeof personaService;
        "mail.sound_effects": typeof soundEffects;
        "mail.store": typeof storeService;
        "mail.suggestion": typeof suggestionService;
    }
}
