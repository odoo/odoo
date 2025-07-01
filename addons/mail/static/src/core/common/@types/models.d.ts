declare module "models" {
    import { Attachment as AttachmentClass } from "@mail/core/common/attachment_model";
    import { CannedResponse as CannedResponseClass } from "@mail/core/common/canned_response_model";
    import { ChannelMember as ChannelMemberClass } from "@mail/core/common/channel_member_model";
    import { ChatHub as ChatHubClass } from "@mail/core/common/chat_hub_model";
    import { ChatWindow as ChatWindowClass } from "@mail/core/common/chat_window_model";
    import { Composer as ComposerClass } from "@mail/core/common/composer_model";
    import { Country as CountryClass } from "@mail/core/common/country_model";
    import { Failure as FailureClass } from "@mail/core/common/failure_model";
    import { Follower as FollowerClass } from "@mail/core/common/follower_model";
    import { LinkPreview as LinkPreviewClass } from "@mail/core/common/link_preview_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { MessageReactions as MessageReactionsClass } from "@mail/core/common/message_reactions_model";
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";
    import { Persona as PersonaClass } from "@mail/core/common/persona_model";
    import { ResGroups as ResGroupsClass } from "@mail/core/common/res_groups_model";
    import { Settings as SettingsClass } from "@mail/core/common/settings_model";
    import { Store as StoreClass } from "@mail/core/common/store_service";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";
    import { Volume as VolumeClass } from "@mail/core/common/volume_model";

    // define interfaces for jsdoc, including with patches
    export interface Attachment extends AttachmentClass {}
    export interface CannedResponse extends CannedResponseClass {}
    export interface ChannelMember extends ChannelMemberClass {}
    export interface ChatHub extends ChatHubClass {}
    export interface ChatWindow extends ChatWindowClass {}
    export interface Composer extends ComposerClass {}
    export interface Country extends CountryClass {}
    export interface Failure extends FailureClass {}
    export interface Follower extends FollowerClass {}
    export interface LinkPreview extends LinkPreviewClass {}
    export interface Message extends MessageClass {}
    export interface MessageReactions extends MessageReactionsClass {}
    export interface Notification extends NotificationClass {}
    export interface Persona extends PersonaClass {}
    export interface ResGroups extends ResGroupsClass {}
    export interface Settings extends SettingsClass {}
    export interface Store extends StoreClass {}
    export interface Thread extends ThreadClass {}
    export interface Volume extends VolumeClass {}

    // required to propagate types in relational fields
    export interface Models {
        "Attachment": Attachment,
        "mail.canned.response": CannedResponse,
        "ChannelMember": ChannelMember,
        "ChatHub": ChatHub,
        "ChatWindow": ChatWindow,
        "Composer": Composer,
        "Country": Country,
        "Failure": Failure,
        "Follower": Follower,
        "LinkPreview": LinkPreview,
        "Message": Message,
        "MessageReactions": MessageReactions,
        "Notification": Notification,
        "Persona": Persona,
        "res.groups": ResGroups,
        "Settings": Settings,
        "Store": Store,
        "Thread": Thread,
        "Volume": Volume,
    }
}
