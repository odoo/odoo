declare module "models" {
    import { Chatbot as ChatbotClass } from "@im_livechat/core/common/chatbot_model";
    import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/core/common/chatbot_script_model";
    import { ChatbotScriptStep as ChatbotScriptStepClass } from "@im_livechat/core/common/chatbot_script_step_model";
    import { ChatbotScriptStepAnswer as ChatbotScriptStepAnswerClass } from "@im_livechat/core/common/chatbot_script_step_answer_model";
    import { ChatbotStep as ChatbotStepClass } from "@im_livechat/core/common/chatbot_step_model";
    import { LivechatChannel as LivechatChannelClass } from "@im_livechat/core/common/livechat_channel_model";
    import { LivechatChannelRule as LivechatChannelRuleClass } from "@im_livechat/core/common/livechat_channel_rule_model";
    import { LivechatConversationTag as LivechatConversationTagClass } from "@im_livechat/core/common/livechat_conversation_tag_model";
    import { LivechatExpertise as LivechatExpertiseClass } from "@im_livechat/core/common/livechat_expertise_model";

    export interface Chatbot extends ChatbotClass {}
    export interface ChatbotScript extends ChatbotScriptClass {}
    export interface ChatbotScriptStep extends ChatbotScriptStepClass {}
    export interface ChatbotScriptStepAnswer extends ChatbotScriptStepAnswerClass {}
    export interface ChatbotStep extends ChatbotStepClass {}
    export interface LivechatChannel extends LivechatChannelClass {}
    export interface LivechatChannelRule extends LivechatChannelRuleClass {}
    export interface LivechatConversationTag extends LivechatConversationTagClass {}
    export interface LivechatExpertise extends LivechatExpertiseClass {}

    export interface ChatWindow {
        livechatStep: undefined|"CONFIRM_CLOSE"|"FEEDBACK";
    }
    export interface DataResponse {
        chatbot_step: ChatbotStep;
    }
    export interface Message {
        chatbotStep: ChatbotStep;
    }
    export interface ResPartner {
        livechat_expertise: String[];
        livechat_languages: String[];
    }
    export interface ResUsers {
        is_livechat_manager: boolean;
        livechat_expertise_ids: LivechatExpertise[];
    }
    export interface Store {
        Chatbot: StaticMailRecord<Chatbot, typeof ChatbotClass>;
        "chatbot.script": StaticMailRecord<ChatbotScript, typeof ChatbotScriptClass>;
        "chatbot.script.answer": StaticMailRecord<ChatbotScriptStepAnswer, typeof ChatbotScriptStepAnswerClass>;
        "chatbot.script.step": StaticMailRecord<ChatbotScriptStep, typeof ChatbotScriptStepClass>;
        ChatbotStep: StaticMailRecord<ChatbotStep, typeof ChatbotStepClass>;
        "im_livechat.channel": StaticMailRecord<LivechatChannel, typeof LivechatChannelClass>;
        "im_livechat.channel.rule": StaticMailRecord<LivechatChannelRule, typeof LivechatChannelRuleClass>;
        "im_livechat.conversation.tag": StaticMailRecord<LivechatConversationTag, typeof LivechatConversationTagClass>;
        "im_livechat.expertise": StaticMailRecord<LivechatExpertise, typeof LivechatExpertiseClass>;
    }
    export interface Thread {
        composerDisabled: Readonly<boolean>;
        composerDisabledText: Readonly<string>;
        livechat_conversation_tag_ids: LivechatConversationTag[];
        livechat_end_dt: import("luxon").DateTime;
        livechat_operator_id: ResPartner;
        livechatVisitorMember: ChannelMember;
        open_chat_window: true|undefined;
        livechat_lang_id: ResLang;
    }

    export interface Models {
        Chatbot: Chatbot;
        "chatbot.script": ChatbotScript;
        "chatbot.script.answer": ChatbotScriptStepAnswer;
        "chatbot.script.step": ChatbotScriptStep;
        ChatbotStep: ChatbotStep;
        "im_livechat.channel": LivechatChannel;
        "im_livechat.channel.rule": LivechatChannelRule;
        "im_livechat.conversation.tag": LivechatConversationTag;
        "im_livechat.expertise": LivechatExpertise;
    }
}
