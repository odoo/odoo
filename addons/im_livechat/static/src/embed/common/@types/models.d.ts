declare module "models" {
    import { ChatbotScriptStep as ChatbotScriptStepClass } from "@im_livechat/embed/common/chatbot/chatbot_script_step_model";
    import { ChatbotStep as ChatbotStepClass } from "@im_livechat/embed/common/chatbot/chatbot_step_model";
    import { Chatbot as ChatbotClass } from "@im_livechat/embed/common/chatbot/chatbot_model";
    import { ChatbotScriptStepAnswer as ChatbotScriptStepAnswerClass } from "@im_livechat/embed/common/chatbot/chatbot_script_step_answer_model";
    import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/embed/common/chatbot/chatbot_script_model";
    import { LivechatRule as LivechatRuleClass } from "@im_livechat/embed/common/livechat/livechat_rule_model";

    export interface ChatbotScriptStep extends ChatbotScriptStepClass { }
    export interface ChatbotStep extends ChatbotStepClass { }
    export interface Chatbot extends ChatbotClass { }
    export interface ChatbotScriptStepAnswer extends ChatbotScriptStepAnswerClass { }
    export interface ChatbotScript extends ChatbotScriptClass { }
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
        "ChatbotScript": ChatbotScript,
        "LivechatRule": LivechatRule,
    }
}
