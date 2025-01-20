declare module "models" {
    import { LivechatRule as LivechatRuleClass } from "@im_livechat/embed/common/livechat/livechat_rule_model";

    export interface LivechatRule extends LivechatRuleClass { }

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

    export interface Models {
        "ChatbotScriptStep": ChatbotScriptStep,
        "ChatbotStep": ChatbotStep,
        "Chatbot": Chatbot,
        "ChatbotScriptStepAnswer": ChatbotScriptStepAnswer,
        "chatbot.script": ChatbotScript,
        "LivechatRule": LivechatRule,
    }
}
