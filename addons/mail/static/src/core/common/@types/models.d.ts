declare module "models" {
    import { Activity as ActivityClass } from "@mail/core/common/activity_model";
    import { Attachment as AttachmentClass } from "@mail/core/common/attachment_model";
    import { CannedResponse as CannedResponseClass } from "@mail/core/common/canned_response_model";
    import { ChatHub as ChatHubClass } from "@mail/core/common/chat_hub_model";
    import { ChatWindow as ChatWindowClass } from "@mail/core/common/chat_window_model";
    import { Composer as ComposerClass } from "@mail/core/common/composer_model";
    import { Country as CountryClass } from "@mail/core/common/country_model";
    import { DataResponse as DataResponseClass } from "@mail/core/common/data_response_model";
    import { DiscussCallHistory as DiscussCallHistoryClass } from "@mail/core/common/discuss_call_history_model";
    import { Failure as FailureClass } from "@mail/core/common/failure_model";
    import { Follower as FollowerClass } from "@mail/core/common/follower_model";
    import { LinkPreview as LinkPreviewClass } from "@mail/core/common/link_preview_model";
    import { MailActivityType as MailActivityTypeClass } from "@mail/core/common/mail_activity_type_model";
    import { MailGuest as MailGuestClass } from "@mail/core/common/mail_guest_model";
    import { MailMessageSubtype as MailMessageSubtypeClass } from "@mail/core/common/mail_message_subtype_model";
    import { MailTemplate as MailTemplateClass } from "@mail/core/common/mail_template_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { MessageLinkPreview as MessageLinkPreviewClass } from "@mail/core/common/message_link_preview_model";
    import { MessageReactions as MessageReactionsClass } from "@mail/core/common/message_reactions_model";
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";
    import { ResCompany as ResCompanyClass } from "@mail/core/common/res_company_model";
    import { ResGroups as ResGroupsClass } from "@mail/core/common/res_groups_model";
    import { ResGroupsPrivilege as ResGroupsPrivilegeClass } from "@mail/core/common/res_groups_privilege_model";
    import { ResLang as ResLangClass } from "@mail/core/common/res_lang_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";
    import { ResRole as ResRoleClass } from "@mail/core/common/res_role_model";
    import { ResUsers as ResUsersClass } from "@mail/core/common/res_users_model";
    import { Settings as SettingsClass } from "@mail/core/common/settings_model";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";
    import { Volume as VolumeClass } from "@mail/core/common/volume_model";

    export interface Activity extends ActivityClass {}
    export interface Attachment extends AttachmentClass {}
    export interface CannedResponse extends CannedResponseClass {}
    export interface ChatHub extends ChatHubClass {}
    export interface ChatWindow extends ChatWindowClass {}
    export interface Composer extends ComposerClass {}
    export interface Country extends CountryClass {}
    export interface DataResponse extends DataResponseClass {}
    export interface DiscussCallHistory extends DiscussCallHistoryClass {}
    export interface Failure extends FailureClass {}
    export interface Follower extends FollowerClass {}
    export interface LinkPreview extends LinkPreviewClass {}
    export interface MailActivityType extends MailActivityTypeClass {}
    export interface MailGuest extends MailGuestClass {}
    export interface MailMessageSubtype extends MailMessageSubtypeClass {}
    export interface MailTemplate extends MailTemplateClass {}
    export interface Message extends MessageClass {}
    export interface MessageLinkPreview extends MessageLinkPreviewClass {}
    export interface MessageReactions extends MessageReactionsClass {}
    export interface Notification extends NotificationClass {}
    export interface ResCompany extends ResCompanyClass {}
    export interface ResGroups extends ResGroupsClass {}
    export interface ResGroupsPrivilege extends ResGroupsPrivilegeClass {}
    export interface ResLang extends ResLangClass {}
    export interface ResPartner extends ResPartnerClass {}
    export interface ResRole extends ResRoleClass {}
    export interface ResUsers extends ResUsersClass {}
    export interface Settings extends SettingsClass {}
    export interface Thread extends ThreadClass {}
    export interface Volume extends VolumeClass {}

    export interface Store {
        ChatHub: StaticMailRecord<ChatHub, typeof ChatHubClass>;
        ChatWindow: StaticMailRecord<ChatWindow, typeof ChatWindowClass>;
        Composer: StaticMailRecord<Composer, typeof ComposerClass>;
        DataResponse: StaticMailRecord<DataResponse, typeof DataResponseClass>;
        "discuss.call.history": StaticMailRecord<DiscussCallHistory, typeof DiscussCallHistoryClass>;
        Failure: StaticMailRecord<Failure, typeof FailureClass>;
        "ir.attachment": StaticMailRecord<Attachment, typeof AttachmentClass>;
        "mail.activity": StaticMailRecord<Activity, typeof ActivityClass>;
        "mail.activity.type": StaticMailRecord<MailActivityType, typeof MailActivityTypeClass>;
        "mail.canned.response": StaticMailRecord<CannedResponse, typeof CannedResponseClass>;
        "mail.followers": StaticMailRecord<Follower, typeof FollowerClass>;
        "mail.guest": StaticMailRecord<MailGuest, typeof MailGuestClass>;
        "mail.link.preview": StaticMailRecord<LinkPreview, typeof LinkPreviewClass>;
        "mail.message": StaticMailRecord<Message, typeof MessageClass>;
        "mail.message.link.preview": StaticMailRecord<MessageLinkPreview, typeof MessageLinkPreviewClass>;
        "mail.message.subtype": StaticMailRecord<MailMessageSubtype, typeof MailMessageSubtypeClass>;
        "mail.notification": StaticMailRecord<Notification, typeof NotificationClass>;
        "mail.template": StaticMailRecord<MailTemplate, typeof MailTemplateClass>;
        MessageReactions: StaticMailRecord<MessageReactions, typeof MessageReactionsClass>;
        "res.company": StaticMailRecord<ResCompany, typeof ResCompanyClass>;
        "res.country": StaticMailRecord<Country, typeof CountryClass>;
        "res.groups": StaticMailRecord<ResGroups, typeof ResGroupsClass>;
        "res.groups.privilege": StaticMailRecord<ResGroupsPrivilege, typeof ResGroupsPrivilegeClass>;
        "res.lang": StaticMailRecord<ResLang, typeof ResLangClass>;
        "res.partner": StaticMailRecord<ResPartner, typeof ResPartnerClass>;
        "res.role": StaticMailRecord<ResRole, typeof ResRoleClass>;
        "res.users": StaticMailRecord<ResUsers, typeof ResUsersClass>;
        Settings: StaticMailRecord<Settings, typeof SettingsClass>;
        Thread: StaticMailRecord<Thread, typeof ThreadClass>;
        Volume: StaticMailRecord<Volume, typeof VolumeClass>;
    }

    export interface Models {
        ChatHub: ChatHub;
        ChatWindow: ChatWindow;
        Composer: Composer;
        DataResponse: DataResponse;
        "discuss.call.history": DiscussCallHistory;
        Failure: Failure;
        "ir.attachment": Attachment;
        "mail.activity": Activity;
        "mail.activity.type": MailActivityType;
        "mail.canned.response": CannedResponse;
        "mail.followers": Follower;
        "mail.guest": MailGuest;
        "mail.link.preview": LinkPreview;
        "mail.message": Message;
        "mail.message.link.preview": MessageLinkPreview;
        "mail.message.subtype": MailMessageSubtype;
        "mail.notification": Notification;
        "mail.template": MailTemplate;
        MessageReactions: MessageReactions;
        "res.company": ResCompany;
        "res.country": Country;
        "res.groups": ResGroups;
        "res.groups.privilege": ResGroupsPrivilege;
        "res.lang": ResLang;
        "res.partner": ResPartner;
        "res.role": ResRole;
        "res.users": ResUsers;
        Settings: Settings;
        Thread: Thread;
        Volume: Volume;
    }
}
