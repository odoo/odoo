declare module "models" {
    import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/embed/common/chatbot/chatbot_script_model";

    export interface ChatbotScript extends ChatbotScriptClass { }
    export interface Thread {
        operator: Persona,
    }

    export interface Models {
        "ChatbotScript": ChatbotScript,
    }
}
