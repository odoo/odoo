declare module "models" {
    import { Chatbot as ChatbotClass } from "@im_livechat/core/common/chatbot_model";
    import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/core/common/chatbot_script_model";
    import { ChatbotScriptStep as ChatbotScriptStepClass } from "@im_livechat/core/common/chatbot_script_step_model";
    import { ChatbotScriptStepAnswer as ChatbotScriptStepAnswerClass } from "@im_livechat/core/common/chatbot_script_step_answer_model";
    import { ChatbotStep as ChatbotStepClass } from "@im_livechat/core/common/chatbot_step_model";
    import { LivechatChannel as LivechatChannelClass } from "@im_livechat/core/common/livechat_channel_model";

    export interface Chatbot extends ChatbotClass {}
    export interface ChatbotScript extends ChatbotScriptClass {}
    export interface ChatbotScriptStep extends ChatbotScriptStepClass {}
    export interface ChatbotScriptStepAnswer extends ChatbotScriptStepAnswerClass {}
    export interface ChatbotStep extends ChatbotStepClass {}
    export interface LivechatChannel extends LivechatChannelClass {}

    export interface ChatWindow {
        livechatStep: unknown;
    }
    export interface Message {
        chatbotStep: ChatbotStep;
    }
    export interface Thread {
        composerDisabled: Readonly<boolean>;
        composerDisabledText: Readonly<null|string>;
        livechat_operator_id: Persona;
        livechatVisitorMember: ChannelMember;
        open_chat_window: unknown;
    }
    export interface Store {
        Chatbot: Chatbot;
        "chatbot.script": ChatbotScript;
        "chatbot.script.step": ChatbotScriptStep;
        "chatbot.script.answer": ChatbotScriptStepAnswer;
        ChatbotStep: ChatbotStep;
        "im_livechat.channel": LivechatChannel;
    }

    export interface Models {
        Chatbot: Chatbot;
        "chatbot.script": ChatbotScript;
        "chatbot.script.step": ChatbotScriptStep;
        "chatbot.script.answer": ChatbotScriptStepAnswer;
        ChatbotStep: ChatbotStep;
        "im_livechat.channel": LivechatChannel;
    }
}
