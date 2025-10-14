declare module "models" {
    export interface DiscussChannel {
        storeAsActiveLivechats: Store;
    }
    export interface Message {
        disableChatbotAnswers: boolean;
    }
    export interface Store {
        activeLivechats: DiscussChannel[];
        guest_token: null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        _prevComposerDisabled: boolean;
        _toggleChatbot: boolean;
        chatbot: Chatbot;
        chatbotTypingMessage: Message;
        hasWelcomeMessage: Readonly<boolean>;
        isLastMessageFromCustomer: Readonly<boolean>;
        livechat_operator_id: ResPartner;
        livechatWelcomeMessage: Message;
        readyToSwapDeferred: Deferred;
        requested_by_operator: boolean;
    }
}
