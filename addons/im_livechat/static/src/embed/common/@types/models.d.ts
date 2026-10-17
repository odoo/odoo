declare module "models" {
    import { Attachment as AttachmentClass } from "@mail/core/common/attachment_model";
    import { ChatWindow as ChatWindowClass } from "@mail/core/common/chat_window_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Attachment extends Patch<AttachmentClass, typeof import("@im_livechat/embed/common/attachment_model_patch").attachmentPatch, "isViewable"> {}
    export interface ChatWindow extends Patch<ChatWindowClass, typeof import("@im_livechat/embed/common/chat_window_model_patch").chatWindowModelPatch> {}
    export interface DiscussChannel extends Patch<DiscussChannelClass, typeof import("@im_livechat/embed/common/discuss_channel_model_patch").discussChannelPatch> {
        livechatWelcomeMessage: Message;
        storeAsActiveVisitorLivechats: Store;
    }
    export interface Message extends Patch<MessageClass, typeof import("@im_livechat/embed/common/message_model_patch").messagePatch> {
        disableChatbotAnswers: boolean;
        isWelcomeMessage: boolean;
    }
    export interface Store extends Patch<StoreClass, typeof import("@im_livechat/embed/common/store_service_patch").StorePatch> {
        activeVisitorLivechats: DiscussChannel[];
        guest_token: string|null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@im_livechat/embed/common/thread_model_patch").threadPatch> {
        _prevComposerDisabled: boolean;
        readyToSwapPromise: Promise<void>;
        resolveReadyToSwap: (value: unknown) => void;
    }
}
