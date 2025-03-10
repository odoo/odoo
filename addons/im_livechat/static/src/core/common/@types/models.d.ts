import { ChatbotScriptStep as ChatbotScriptStepClass } from "@im_livechat/core/common/chatbot_script_step_model";
import { ChatbotStep as ChatbotStepClass } from "@im_livechat/core/common/chatbot_step_model";
import { Chatbot as ChatbotClass } from "@im_livechat/core/common/chatbot_model";
import { ChatbotScriptStepAnswer as ChatbotScriptStepAnswerClass } from "@im_livechat/core/common/chatbot_script_step_answer_model";
import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/core/common/chatbot_script_model";

declare module "models" {
    export interface Persona {
        livechat_languages: String[],
        livechat_expertise: String[],
    }
    export interface Thread {
        livechat_operator_id: Persona,
    }
    export interface ChatbotScriptStep extends ChatbotScriptStepClass { }
    export interface ChatbotStep extends ChatbotStepClass { }
    export interface Chatbot extends ChatbotClass { }
    export interface ChatbotScriptStepAnswer extends ChatbotScriptStepAnswerClass { }
    export interface ChatbotScript extends ChatbotScriptClass { }

}
