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
    import { gifPickerService } from "@mail/discuss/gif_picker/common/gif_picker_service";
    import { mailCoreCommon } from "@mail/core/common/mail_core_common_service";
    import { mailCoreWeb } from "@mail/core/web/mail_core_web_service";
    import { messagePinService } from "@mail/discuss/message_pin/common/message_pin_service"
    import { messageService } from "@mail/core/common/message_service";
    import { messagingService } from "@mail/core/common/messaging_service";
    import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
    import { outOfFocusService } from "@mail/core/common/out_of_focus_service";
    import { personaService } from "@mail/core/common/persona_service";
    import { rtcService } from "@mail/discuss/call/common/rtc_service";
    import { soundEffects } from "@mail/core/common/sound_effects_service";
    import { storeService } from "@mail/core/common/store_service";
    import { suggestionService } from "@mail/core/common/suggestion_service";
    import { threadService } from "@mail/core/common/thread_service";
    import { userSettingsService } from "@mail/core/common/user_settings_service";

    export interface Services {
        "discuss.channel.member": ReturnType<typeof channelMemberService.start>;
        "discuss.core.common": ReturnType<typeof discussCoreCommon.start>;
        "discuss.core.public": ReturnType<typeof discussCorePublic.start>;
        "discuss.core.web": ReturnType<typeof discussCoreWeb.start>;
        "discuss.gifPicker": ReturnType<typeof gifPickerService.start>;
        "discuss.message.pin": ReturnType<typeof messagePinService.start>;
        "discuss.rtc": ReturnType<typeof rtcService.start>;
        "discuss.typing": ReturnType<typeof discussTypingService.start>;
        "mail.activity": ReturnType<typeof activityService.start>;
        "mail.attachment": ReturnType<typeof attachmentService.start>;
        "mail.attachment_upload": ReturnType<typeof attachmentUploadService.start>;
        "mail.chat_window": ReturnType<typeof chatWindowService.start>;
        "mail.core.common": ReturnType<typeof mailCoreCommon.start>;
        "mail.core.web": ReturnType<typeof mailCoreWeb.start>;
        "mail.message": ReturnType<typeof messageService.start>;
        "mail.messaging": ReturnType<typeof messagingService.start>;
        "mail.notification.permission": ReturnType<typeof notificationPermissionService.start>;
        "mail.out_of_focus": ReturnType<typeof outOfFocusService.start>;
        "mail.persona": ReturnType<typeof personaService.start>;
        "mail.sound_effects": ReturnType<typeof soundEffects.start>;
        "mail.store": ReturnType<typeof storeService.start>;
        "mail.suggestion": ReturnType<typeof suggestionService.start>;
        "mail.thread": ReturnType<typeof threadService.start>;
        "mail.user_settings": ReturnType<typeof userSettingsService.start>;
    }
}
