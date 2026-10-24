declare module "models" {
    import { Activity as ActivityClass } from "@mail/core/common/activity_model";
    import { Attachment as AttachmentClass } from "@mail/core/common/attachment_model";
    import { CannedResponse as CannedResponseClass } from "@mail/core/common/canned_response_model";
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { ChatHub as ChatHubClass } from "@mail/core/common/chat_hub_model";
    import { ChatWindow as ChatWindowClass } from "@mail/core/common/chat_window_model";
    import { Composer as ComposerClass } from "@mail/core/common/composer_model";
    import { Country as CountryClass } from "@mail/core/common/country_model";
    import { DataResponse as DataResponseClass } from "@mail/core/common/data_response_model";
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app/discuss_app_model";
    import { DiscussCallHistory as DiscussCallHistoryClass } from "@mail/core/common/discuss_call_history_model";
    import { DiscussCategory as DiscussCategoryClass } from "@mail/discuss/core/common/discuss_category_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { Failure as FailureClass } from "@mail/core/common/failure_model";
    import { Follower as FollowerClass } from "@mail/core/common/follower_model";
    import { LinkPreview as LinkPreviewClass } from "@mail/core/common/link_preview_model";
    import { MailActivityType as MailActivityTypeClass } from "@mail/core/common/mail_activity_type_model";
    import { MailGuest as MailGuestClass } from "@mail/core/common/mail_guest_model";
    import { MailMessageSubtype as MailMessageSubtypeClass } from "@mail/core/common/mail_message_subtype_model";
    import { MailPollModel as MailPollModelClass } from "@mail/core/common/mail_poll_model";
    import { MailPollOptionModel as MailPollOptionModelClass } from "@mail/core/common/mail_poll_option_model";
    import { MailPollVote as MailPollVoteClass } from "@mail/core/common/mail_poll_vote_model";
    import { MailTemplate as MailTemplateClass } from "@mail/core/common/mail_template_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { MessageLinkPreview as MessageLinkPreviewClass } from "@mail/core/common/message_link_preview_model";
    import { MessageReactions as MessageReactionsClass } from "@mail/core/common/message_reactions_model";
    import { MessagingMenu as MessagingMenuClass } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
    import { MessagingMenuTab as MessagingMenuTabClass } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";
    import { MessagingMenuUIState as MessagingMenuUIStateClass } from "@mail/core/public_web/messaging_menu/messaging_menu_ui_state_model";
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";
    import { ResCompany as ResCompanyClass } from "@mail/core/common/res_company_model";
    import { ResCurrency as ResCurrencyClass } from "@mail/core/common/res_currency_model";
    import { ResGroups as ResGroupsClass } from "@mail/core/common/res_groups_model";
    import { ResGroupsPrivilege as ResGroupsPrivilegeClass } from "@mail/core/common/res_groups_privilege_model";
    import { ResLang as ResLangClass } from "@mail/core/common/res_lang_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";
    import { ResRole as ResRoleClass } from "@mail/core/common/res_role_model";
    import { ResUsers as ResUsersClass } from "@mail/core/common/res_users_model";
    import { ResUsersSettings as ResUsersSettingsClass } from "@mail/core/common/res_users_settings_model";
    import { Rtc as RtcClass } from "@mail/discuss/call/common/rtc_service";
    import { RtcSession as RtcSessionClass } from "@mail/discuss/call/common/rtc_session_model";
    import { ScheduledMessage as ScheduledMessageClass } from "@mail/chatter/common/scheduled_message_model";
    import { Settings as SettingsClass } from "@mail/core/common/settings_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";
    import { VoiceMetadata as VoiceMetadataClass } from "@mail/discuss/core/common/voice_metadata_model";
    import { Volume as VolumeClass } from "@mail/core/common/volume_model";

    /** Keys of `T` without index signatures (e.g. classes built from untyped mixins). */
    type KnownKeys<T> = keyof { [K in keyof T as string extends K ? never : number extends K ? never : K]: T[K] };
    /**
     * Members added by a `patchModel` extension that are not already on the class. `Overrides`
     * lists members already added by an earlier patch, which must not be typed twice.
     */
    type Patch<Base, T, Overrides extends PropertyKey = never> = Omit<T, KnownKeys<Base> | Overrides>;

    type StaticMailRecord<ClassInterface, JSClassType> = Omit<JSClassType, "get" | "insert" | "records"> & {
        new (...args: any[]): ClassInterface;
        get: (data: any) => ClassInterface;
        insert: <D extends object | object[]>(data: D, options?: object) => D extends object[] ? ClassInterface[] : ClassInterface;
        records: { [localId: string]: ClassInterface };
    };

    export interface Activity
        extends ActivityClass,
            Patch<ActivityClass, typeof import("@mail/core/web/activity_model_patch").activityPatch> {}

    export interface Attachment
        extends AttachmentClass,
            Patch<AttachmentClass, typeof import("@mail/discuss/core/common/attachment_model_patch").attachmentPatch>,
            Patch<AttachmentClass, typeof import("@mail/discuss/voice_message/common/attachment_model_patch").attachmentPatch> {}

    export interface CannedResponse extends CannedResponseClass {}

    export interface ChannelMember
        extends ChannelMemberClass,
            Patch<ChannelMemberClass, typeof import("@mail/discuss/call/common/channel_member_model_patch").ChannelMemberPatch> {}

    export interface ChatHub extends ChatHubClass {}

    export interface ChatWindow
        extends ChatWindowClass,
            Patch<ChatWindowClass, typeof import("@mail/core/web/chat_window_model_patch").chatWindowPatch> {}

    export interface Composer
        extends ComposerClass,
            Patch<ComposerClass, typeof import("@mail/discuss/voice_message/common/composer_model_patch").composerPatch> {}

    export interface Country extends CountryClass {}

    export interface DataResponse extends DataResponseClass {}

    export interface DiscussApp
        extends DiscussAppClass,
            Patch<DiscussAppClass, typeof import("@mail/discuss/core/public/discuss_app/discuss_app_model_patch").discussAppPatch> {}

    export interface DiscussCallHistory extends DiscussCallHistoryClass {}

    export interface DiscussCategory extends DiscussCategoryClass {}

    export interface DiscussChannel
        extends DiscussChannelClass,
            Thread,
            Patch<DiscussChannelClass, typeof import("@mail/discuss/core/public_web/discuss_channel_model_patch").discussChannelPatch>,
            Patch<DiscussChannelClass, typeof import("@mail/discuss/core/web/discuss_channel_model_patch").discussChannelPatch>,
            Patch<DiscussChannelClass, typeof import("@mail/discuss/call/common/discuss_channel_model_patch").DiscussChannelPatch>,
            Patch<DiscussChannelClass, typeof import("@mail/discuss/call/public_web/discuss_channel_model_patch").DiscussChannelPatch, "isCallDisplayedInChatWindow"> {}

    export interface Failure extends FailureClass {}

    export interface Follower extends FollowerClass {}

    export interface LinkPreview extends LinkPreviewClass {}

    export interface MailActivityType extends MailActivityTypeClass {}

    export interface MailGuest
        extends MailGuestClass,
            Patch<MailGuestClass, typeof import("@mail/discuss/core/common/mail_guest_model_patch").mailGuestPatch>,
            Patch<MailGuestClass, typeof import("@mail/discuss/call/common/mail_guest_model_patch").mailGuestPatch> {}

    export interface MailMessageSubtype extends MailMessageSubtypeClass {}

    export interface MailPollModel extends MailPollModelClass {}

    export interface MailPollOptionModel extends MailPollOptionModelClass {}

    export interface MailPollVote extends MailPollVoteClass {}

    export interface MailTemplate extends MailTemplateClass {}

    export interface Message
        extends MessageClass,
            Patch<MessageClass, typeof import("@mail/core/public_web/message_model_patch").messagePatch>,
            Patch<MessageClass, typeof import("@mail/core/web/message_model_patch").messagePatch>,
            Patch<MessageClass, typeof import("@mail/discuss/core/common/message_model_patch").messagePatch>,
            Patch<MessageClass, typeof import("@mail/discuss/call/common/message_model_patch").messagePatch> {}

    export interface MessageLinkPreview extends MessageLinkPreviewClass {}

    export interface MessageReactions extends MessageReactionsClass {}

    export interface MessagingMenu
        extends MessagingMenuClass,
            Patch<MessagingMenuClass, typeof import("@mail/discuss/core/public_web/messaging_menu_model_patch").messagingMenuPatch> {}

    export interface MessagingMenuTab
        extends MessagingMenuTabClass,
            Patch<MessagingMenuTabClass, typeof import("@mail/discuss/core/public_web/messaging_menu_tab_model_patch").messagingMenuTabPatch> {}

    export interface MessagingMenuUIState
        extends MessagingMenuUIStateClass,
            Patch<MessagingMenuUIStateClass, typeof import("@mail/discuss/core/public_web/messaging_menu_ui_state_model_patch").messagingMenuUIStateModelPatch> {}

    export interface Notification extends NotificationClass {}

    export interface ResCompany extends ResCompanyClass {}

    export interface ResCurrency extends ResCurrencyClass {}

    export interface ResGroups extends ResGroupsClass {}

    export interface ResGroupsPrivilege extends ResGroupsPrivilegeClass {}

    export interface ResLang extends ResLangClass {}

    export interface ResPartner
        extends ResPartnerClass,
            Patch<ResPartnerClass, typeof import("@mail/discuss/core/common/res_partner_model_patch").resPartnerPatch>,
            Patch<ResPartnerClass, typeof import("@mail/discuss/call/common/res_partner_model_patch").resPartnerPatch> {}

    export interface ResRole extends ResRoleClass {}

    export interface ResUsers
        extends ResUsersClass,
            ResPartner {}

    export interface ResUsersSettings extends ResUsersSettingsClass {}

    export interface Rtc extends RtcClass {}

    export interface RtcSession extends RtcSessionClass {}

    export interface ScheduledMessage
        extends ScheduledMessageClass,
            Patch<ScheduledMessageClass, typeof import("@mail/chatter/web/scheduled_message_model_patch").ScheduledMessagePatch> {}

    export interface Settings extends SettingsClass {}

    export interface Store
        extends StoreClass,
            Patch<StoreClass, typeof import("@mail/core/public_web/store_service_patch").storePatch>,
            Patch<StoreClass, typeof import("@mail/core/web/store_service_patch").StorePatch>,
            Patch<StoreClass, typeof import("@mail/discuss/core/common/store_service_patch").storeServicePatch>,
            Patch<StoreClass, typeof import("@mail/discuss/core/public_web/store_service_patch").StorePatch>,
            Patch<StoreClass, typeof import("@mail/discuss/core/web/store_service_patch").StorePatch, "onLinkFollowed">,
            Patch<StoreClass, typeof import("@mail/discuss/call/common/store_service_patch").StorePatch, "sortMembers">,
            Patch<StoreClass, typeof import("@mail/discuss/call/public/store_service_patch").StorePatch, "_hasFullscreenUrlOnUpdate"> {
        ChatHub: StaticMailRecord<ChatHub, typeof ChatHubClass>;
        ChatWindow: StaticMailRecord<ChatWindow, typeof ChatWindowClass>;
        Composer: StaticMailRecord<Composer, typeof ComposerClass>;
        DataResponse: StaticMailRecord<DataResponse, typeof DataResponseClass>;
        "discuss.call.history": StaticMailRecord<DiscussCallHistory, typeof DiscussCallHistoryClass>;
        "discuss.category": StaticMailRecord<DiscussCategory, typeof DiscussCategoryClass>;
        "discuss.channel": StaticMailRecord<DiscussChannel, typeof DiscussChannelClass>;
        "discuss.channel.member": StaticMailRecord<ChannelMember, typeof ChannelMemberClass>;
        "discuss.channel.rtc.session": StaticMailRecord<RtcSession, typeof RtcSessionClass>;
        "discuss.voice.metadata": StaticMailRecord<VoiceMetadata, typeof VoiceMetadataClass>;
        DiscussApp: StaticMailRecord<DiscussApp, typeof DiscussAppClass>;
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
        "mail.poll": StaticMailRecord<MailPollModel, typeof MailPollModelClass>;
        "mail.poll.option": StaticMailRecord<MailPollOptionModel, typeof MailPollOptionModelClass>;
        "mail.poll.vote": StaticMailRecord<MailPollVote, typeof MailPollVoteClass>;
        "mail.scheduled.message": StaticMailRecord<ScheduledMessage, typeof ScheduledMessageClass>;
        "mail.template": StaticMailRecord<MailTemplate, typeof MailTemplateClass>;
        "mail.thread": StaticMailRecord<Thread, typeof ThreadClass>;
        MessageReactions: StaticMailRecord<MessageReactions, typeof MessageReactionsClass>;
        MessagingMenu: StaticMailRecord<MessagingMenu, typeof MessagingMenuClass>;
        MessagingMenuTab: StaticMailRecord<MessagingMenuTab, typeof MessagingMenuTabClass>;
        MessagingMenuUIState: StaticMailRecord<MessagingMenuUIState, typeof MessagingMenuUIStateClass>;
        "res.company": StaticMailRecord<ResCompany, typeof ResCompanyClass>;
        "res.country": StaticMailRecord<Country, typeof CountryClass>;
        "res.currency": StaticMailRecord<ResCurrency, typeof ResCurrencyClass>;
        "res.groups": StaticMailRecord<ResGroups, typeof ResGroupsClass>;
        "res.groups.privilege": StaticMailRecord<ResGroupsPrivilege, typeof ResGroupsPrivilegeClass>;
        "res.lang": StaticMailRecord<ResLang, typeof ResLangClass>;
        "res.partner": StaticMailRecord<ResPartner, typeof ResPartnerClass>;
        "res.role": StaticMailRecord<ResRole, typeof ResRoleClass>;
        "res.users": StaticMailRecord<ResUsers, typeof ResUsersClass>;
        "res.users.settings": StaticMailRecord<ResUsersSettings, typeof ResUsersSettingsClass>;
        "res.users.settings.volumes": StaticMailRecord<Volume, typeof VolumeClass>;
        Rtc: StaticMailRecord<Rtc, typeof RtcClass>;
        Settings: StaticMailRecord<Settings, typeof SettingsClass>;
        Store: StaticMailRecord<Store, typeof StoreClass>;
    }

    export interface Thread
        extends ThreadClass,
            Patch<ThreadClass, typeof import("@mail/core/public_web/thread_model_patch").threadModelPatch>,
            Patch<ThreadClass, typeof import("@mail/core/web/thread_model_patch").threadPatch>,
            Patch<ThreadClass, typeof import("@mail/chatter/common/thread_model_patch").threadPatch>,
            Patch<ThreadClass, typeof import("@mail/chatter/web_portal_project/thread_model_patch").threadPatch>,
            Patch<ThreadClass, typeof import("@mail/chatter/web/thread_model_patch").threadPatch, "fetchThreadData" | "fullComposerCloseRequestList">,
            Patch<ThreadClass, typeof import("@mail/discuss/core/common/thread_model_patch").threadPatch>,
            Patch<ThreadClass, typeof import("@mail/discuss/core/public_web/thread_model_patch").threadPatch, "setAsDiscussThread">,
            Patch<ThreadClass, typeof import("@mail/discuss/call/common/thread_model_patch").ThreadPatch> {}

    export interface VoiceMetadata extends VoiceMetadataClass {}

    export interface Volume extends VolumeClass {}

    export interface Models {
        ChatHub: ChatHub;
        ChatWindow: ChatWindow;
        Composer: Composer;
        DataResponse: DataResponse;
        "discuss.call.history": DiscussCallHistory;
        "discuss.category": DiscussCategory;
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
        "discuss.channel.rtc.session": RtcSession;
        "discuss.voice.metadata": VoiceMetadata;
        DiscussApp: DiscussApp;
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
        "mail.poll": MailPollModel;
        "mail.poll.option": MailPollOptionModel;
        "mail.poll.vote": MailPollVote;
        "mail.scheduled.message": ScheduledMessage;
        "mail.template": MailTemplate;
        "mail.thread": Thread;
        MessageReactions: MessageReactions;
        MessagingMenu: MessagingMenu;
        MessagingMenuTab: MessagingMenuTab;
        MessagingMenuUIState: MessagingMenuUIState;
        "res.company": ResCompany;
        "res.country": Country;
        "res.currency": ResCurrency;
        "res.groups": ResGroups;
        "res.groups.privilege": ResGroupsPrivilege;
        "res.lang": ResLang;
        "res.partner": ResPartner;
        "res.role": ResRole;
        "res.users": ResUsers;
        "res.users.settings": ResUsersSettings;
        "res.users.settings.volumes": Volume;
        Rtc: Rtc;
        Settings: Settings;
        Store: Store;
    }
}
