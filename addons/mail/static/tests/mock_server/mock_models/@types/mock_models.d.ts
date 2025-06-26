declare module "mock_models" {
    import { Base as Base2 } from "@mail/../tests/mock_server/mock_models/base";
    import { DiscussChannel as DiscussChannel2 } from "@mail/../tests/mock_server/mock_models/discuss_channel";
    import { DiscussChannelMember as DiscussChannelMember2 } from "@mail/../tests/mock_server/mock_models/discuss_channel_member";
    import { DiscussChannelRtcSession as DiscussChannelRtcSession2 } from "@mail/../tests/mock_server/mock_models/discuss_channel_rtc_session";
    import { DiscussVoiceMetadata as DiscussVoiceMetadata2 } from "@mail/../tests/mock_server/mock_models/discuss_voice_metadata";
    import { IrAttachment as IrAttachment2 } from "@mail/../tests/mock_server/mock_models/ir_attachment";
    import { MailActivity as MailActivity2 } from "@mail/../tests/mock_server/mock_models/mail_activity";
    import { MailActivityType as MailActivityType2 } from "@mail/../tests/mock_server/mock_models/mail_activity_type";
    import { MailFollowers as MailFollowers2 } from "@mail/../tests/mock_server/mock_models/mail_followers";
    import { MailGuest as MailGuest2 } from "@mail/../tests/mock_server/mock_models/mail_guest";
    import { MailLinkPreview as MailLinkPreview2 } from "@mail/../tests/mock_server/mock_models/mail_link_preview";
    import { MailMessage as MailMessage2 } from "@mail/../tests/mock_server/mock_models/mail_message";
    import { MailMessageReaction as MailMessageReaction2 } from "@mail/../tests/mock_server/mock_models/mail_message_reaction";
    import { MailMessageSubtype as MailMessageSubtype2 } from "@mail/../tests/mock_server/mock_models/mail_message_subtype";
    import { MailNotification as MailNotification2 } from "@mail/../tests/mock_server/mock_models/mail_notification";
    import { MailScheduledMessage as MailScheduledMessage2 } from "@mail/.../tests/mock_server/mock_models/mail_scheduled_message";
    import { MailShortcode as MailShortcode2 } from "@mail/../tests/mock_server/mock_models/mail_shortcode";
    import { MailTemplate as MailTemplate2 } from "@mail/../tests/mock_server/mock_models/mail_template";
    import { MailThread as MailThread2 } from "@mail/../tests/mock_server/mock_models/mail_thread";
    import { MailTrackingValue as MailTrackingValue2 } from "@mail/../tests/mock_server/mock_models/mail_tracking_value";
    import { ResFake as ResFake2 } from "@mail/../tests/mock_server/mock_models/res_fake";
    import { ResPartner as ResPartner2 } from "@mail/../tests/mock_server/mock_models/res_partner";
    import { ResUsers as ResUsers2 } from "@mail/../tests/mock_server/mock_models/res_users";
    import { ResUsersSettings as ResUsersSettings2 } from "@mail/../tests/mock_server/mock_models/res_users_settings";
    import { ResUsersSettingsVolumes as ResUsersSettingsVolumes2 } from "@mail/../tests/mock_server/mock_models/res_users_settings_volumes";

    export interface Base extends Base2 {}
    export interface DiscussChannel extends DiscussChannel2 {}
    export interface DiscussChannelMember extends DiscussChannelMember2 {}
    export interface DiscussChannelRtcSession extends DiscussChannelRtcSession2 {}
    export interface DiscussVoiceMetadata extends DiscussVoiceMetadata2 {}
    export interface IrAttachment extends IrAttachment2 {}
    export interface MailActivity extends MailActivity2 {}
    export interface MailActivityType extends MailActivityType2 {}
    export interface MailFollowers extends MailFollowers2 {}
    export interface MailGuest extends MailGuest2 {}
    export interface MailLinkPreview extends MailLinkPreview2 {}
    export interface MailMessage extends MailMessage2 {}
    export interface MailMessageReaction extends MailMessageReaction2 {}
    export interface MailMessageSubtype extends MailMessageSubtype2 {}
    export interface MailNotification extends MailNotification2 {}
    export interface MailScheduledMessage extends MailScheduledMessage2 {}
    export interface MailShortcode extends MailShortcode2 {}
    export interface MailTemplate extends MailTemplate2 {}
    export interface MailThread extends MailThread2 {}
    export interface MailTrackingValue extends MailTrackingValue2 {}
    export interface ResFake extends ResFake2 {}
    export interface ResPartner extends ResPartner2 {}
    export interface ResUsers extends ResUsers2 {}
    export interface ResUsersSettings extends ResUsersSettings2 {}
    export interface ResUsersSettingsVolumes extends ResUsersSettingsVolumes2 {}

    export interface Models {
        "base": Base,
        "discuss.channel": DiscussChannel,
        "discuss.channel.member": DiscussChannelMember,
        "discuss.channel.rtc.session": DiscussChannelRtcSession,
        "discuss.voice.metadata": DiscussVoiceMetadata,
        "ir.attachment": IrAttachment,
        "mail.activity": MailActivity,
        "mail.activity.type": MailActivityType,
        "mail.followers": MailFollowers,
        "mail.guest": MailGuest,
        "mail.link.preview": MailLinkPreview,
        "mail.message": MailMessage,
        "mail.message.reaction": MailMessageReaction,
        "mail.message.subtype": MailMessageSubtype,
        "mail.notification": MailNotification,
        "mail.scheduled.message": MailScheduledMessage,
        "mail.shortcode": MailShortcode,
        "mail.template": MailTemplate,
        "mail.thread": MailThread,
        "mail.tracking.value": MailTrackingValue,
        "res.fake": ResFake,
        "res.partner": ResPartner,
        "res.users": ResUsers,
        "res.users.settings": ResUsersSettings,
        "res.users.settings.volumes": ResUsersSettingsVolumes,
    }
}
