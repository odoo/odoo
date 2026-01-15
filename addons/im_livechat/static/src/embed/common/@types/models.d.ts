declare module "models" {
    export interface Message {
        disableChatbotAnswers: boolean;
    }
    export interface Store {
        activeLivechats: Thread[];
        guest_token: null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        _toggleChatbot: boolean;
        chatbot: Chatbot;
        chatbotTypingMessage: Message;
        hasWelcomeMessage: Readonly<boolean>;
        isLastMessageFromCustomer: Readonly<boolean>;
        livechat_operator_id: ResPartner;
        livechatWelcomeMessage: Message;
        readyToSwapDeferred: Deferred;
        requested_by_operator: boolean;
        storeAsActiveLivechats: Store;
    }
}
