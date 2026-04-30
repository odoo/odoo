declare module "models" {
    export interface DiscussChannel {
        _toggleChatbot: boolean;
        hasWelcomeMessage: Readonly<boolean>;
        isLastMessageFromCustomer: Readonly<unknown>;
        livechatWelcomeMessage: Message;
        requested_by_operator: boolean;
        storeAsActiveVisitorLivechats: Store;
    }
    export interface Message {
        disableChatbotAnswers: boolean;
    }
    export interface Store {
        activeVisitorLivechats: DiscussChannel[];
        guest_token: null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        _prevComposerDisabled: boolean;
        readyToSwapPromise: Promise<void>;
        resolveReadyToSwap: (value?: void) => void;
    }
}
