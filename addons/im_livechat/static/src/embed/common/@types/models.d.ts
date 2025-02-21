declare module "models" {
    export interface Store {
        activeLivechats: Thread[];
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        _toggleChatbot: boolean;
        chatbot: Chatbot;
        chatbotTypingMessage: Message;
        hasWelcomeMessage: Readonly<boolean>;
        isLastMessageFromCustomer: Readonly<boolean>;
        livechat_active: boolean;
        livechat_operator_id: Persona;
        livechatWelcomeMessage: Message;
        requested_by_operator: boolean;
        storeAsActiveLivechats: Store;
    }
}
