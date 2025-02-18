declare module "models" {
    export interface ChatWindpw {
        hasFeedbackPanel: boolean,
    }

    export interface Message {
        chatbotStep: ChatbotStep,
    }

    export interface Thread {
        livechatWelcomeMessage: Message,
        chatbot: Chatbot,
        requested_by_operator: boolean,
    }

    export interface Store {
        livechat_rule: LivechatChannelRule;
        livechat_available: boolean;
    }

    export interface Models {
        "ChatbotScriptStep": ChatbotScriptStep,
        "ChatbotStep": ChatbotStep,
        "Chatbot": Chatbot,
        "ChatbotScriptStepAnswer": ChatbotScriptStepAnswer,
        "chatbot.script": ChatbotScript,
        "LivechatRule": LivechatRule,
    }
}
