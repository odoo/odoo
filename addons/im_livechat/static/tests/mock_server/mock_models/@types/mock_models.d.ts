declare module "mock_models" {
    import { ChatbotMessage as ChatbotMessage2 } from "../chatbot_message";
    import { ChatbotScriptAnswer as ChatbotScriptAnswer2 } from "../chatbot_script_answer";
    import { ChatbotScriptStep as ChatbotScriptStep2 } from "../chatbot_script_step";
    import { LivechatChannel as LivechatChannel2 } from "../im_livechat_channel";
    import { LivechatChannelMemberHistory as LivechatChannelMemberHistory2 } from "../im_livechat_channel_member_history";

    export interface ChatbotMessage extends ChatbotMessage2 {}
    export interface ChatbotScriptAnswer extends ChatbotScriptAnswer2 {}
    export interface ChatbotScriptStep extends ChatbotScriptStep2 {}
    export interface LivechatChannel extends LivechatChannel2 {}
    export interface LivechatChannelMemberHistory extends LivechatChannelMemberHistory2 {}

    export interface Models {
        "chatbot.message": ChatbotMessage,
        "chatbot.script.answer": ChatbotScriptAnswer,
        "chatbot.script.step": ChatbotScriptStep,
        "im_livechat.channel": LivechatChannel,
        "im_livechat.channel.member.history": LivechatChannelMemberHistory,
    }
}
