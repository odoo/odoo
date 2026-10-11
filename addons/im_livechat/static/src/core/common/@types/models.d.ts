declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { Chatbot as ChatbotClass } from "@im_livechat/core/common/chatbot_model";
    import { ChatbotMessage as ChatbotMessageClass } from "@im_livechat/core/common/chatbot_message_model";
    import { ChatbotScript as ChatbotScriptClass } from "@im_livechat/core/common/chatbot_script_model";
    import { ChatbotScriptStep as ChatbotScriptStepClass } from "@im_livechat/core/common/chatbot_script_step_model";
    import { ChatbotScriptStepAnswer as ChatbotScriptStepAnswerClass } from "@im_livechat/core/common/chatbot_script_step_answer_model";
    import { ChatbotStep as ChatbotStepClass } from "@im_livechat/core/common/chatbot_step_model";
    import { ChatWindow as ChatWindowClass } from "@mail/core/common/chat_window_model";
    import { DataResponse as DataResponseClass } from "@mail/core/common/data_response_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { LivechatChannel as LivechatChannelClass } from "@im_livechat/core/common/livechat_channel_model";
    import { LivechatChannelMemberHistory as LivechatChannelMemberHistoryClass } from "@im_livechat/core/common/livechat_channel_member_history_model";
    import { LivechatChannelRule as LivechatChannelRuleClass } from "@im_livechat/core/common/livechat_channel_rule_model";
    import { LivechatExpertise as LivechatExpertiseClass } from "@im_livechat/core/common/livechat_expertise_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";
    import { ResUsers as ResUsersClass } from "@mail/core/common/res_users_model";
    import { ResUsersSettings as ResUsersSettingsClass } from "@mail/core/common/res_users_settings_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Chatbot extends ChatbotClass {}
    export interface ChatbotMessage extends ChatbotMessageClass {}
    export interface ChatbotScript extends ChatbotScriptClass {}
    export interface ChatbotScriptStep extends ChatbotScriptStepClass {}
    export interface ChatbotScriptStepAnswer extends ChatbotScriptStepAnswerClass {}
    export interface ChatbotStep extends ChatbotStepClass {}
    export interface LivechatChannelMemberHistory extends LivechatChannelMemberHistoryClass {}
    export interface LivechatChannelRule extends LivechatChannelRuleClass {}
    export interface LivechatExpertise extends LivechatExpertiseClass {}

    export interface ChannelMember extends Patch<ChannelMemberClass, typeof import("@im_livechat/core/common/discuss_channel_member_model_patch").discussChannelMemberPatch> {
        livechat_member_type: "agent"|"bot"|"visitor";
    }
    export interface ChatWindow extends Patch<ChatWindowClass, typeof import("@im_livechat/core/common/chat_window_model_patch").chatWindowPatch> {
        confirmCloseResolver: PromiseWithResolvers<boolean>;
        feedbackDoneResolver: PromiseWithResolvers<void>;
    }
    export interface DataResponse extends Patch<DataResponseClass, typeof import("@im_livechat/core/common/data_response_model_patch").dataResponsePatch> {
        chatbot_step: ChatbotStep;
    }
    export interface DiscussChannel extends Patch<DiscussChannelClass, typeof import("@im_livechat/core/common/discuss_channel_model_patch").discussChannelPatch> {
        chatbot: Chatbot;
        chatbot_current_step_id: ChatbotScriptStep;
        chatbotTriggerFailedError: import("@web/core/network/rpc").RPCError|import("@web/core/network/rpc").ConnectionLostError|import("@web/core/network/rpc").ConnectionAbortedError|undefined;
        country_id: Country;
        livechat_agent_history_ids: LivechatChannelMemberHistory[];
        livechat_bot_history_ids: LivechatChannelMemberHistory[];
        livechat_channel_id: LivechatChannel;
        livechat_channel_member_history_ids: LivechatChannelMemberHistory[];
        livechat_customer_history_ids: LivechatChannelMemberHistory[];
        livechat_customer_partner_ids: ResPartner[];
        livechat_end_dt: import("luxon").DateTime;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_lang_id: ResLang;
        livechat_looking_for_help_since_dt: import("luxon").DateTime;
        livechat_note: ReturnType<typeof import("@odoo/owl").markup>|string;
        livechat_operator_id: ResPartner;
        livechat_outcome: string|undefined;
        livechat_status: "in_progress"|"need_help"|undefined;
        livechatNoteText: string|undefined;
        livechatVisitorMember: ChannelMember;
    }
    export interface LivechatChannel
        extends LivechatChannelClass,
            Patch<LivechatChannelClass, typeof import("@im_livechat/core/common/livechat_channel_model_patch").livechatChannelPatch> {
        channel_ids: DiscussChannel[];
    }
    export interface Message extends Patch<MessageClass, typeof import("@im_livechat/core/common/message_model_patch").messagePatch> {
        chatbotStep: ChatbotStep;
    }
    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@im_livechat/core/common/res_partner_model_patch").resPartnerPatch> {
        invite_by_self_count: number|undefined;
        is_available: boolean|undefined;
        lang_name: string|undefined;
        livechat_languages: String[];
        user_livechat_username: string|undefined;
    }
    export interface ResUsers extends Patch<ResUsersClass, typeof import("@im_livechat/core/common/res_users_model_patch").resUsersPatch> {
        is_livechat_manager: boolean;
        livechat_expertise_ids: LivechatExpertise[];
    }
    export interface ResUsersSettings extends Patch<ResUsersSettingsClass, typeof import("@im_livechat/core/common/res_users_settings_model_patch").resUsersSettingsPatch> {
        livechat_expertise_ids: number[];
        livechat_lang_ids: number[];
        livechat_username: string|undefined;
    }
    export interface Store extends Patch<StoreClass, typeof import("@im_livechat/core/common/store_service_patch").storePatch> {
        can_download_transcript: boolean|undefined;
        Chatbot: StaticMailRecord<Chatbot, typeof ChatbotClass>;
        "chatbot.message": StaticMailRecord<ChatbotMessage, typeof ChatbotMessageClass>;
        "chatbot.script": StaticMailRecord<ChatbotScript, typeof ChatbotScriptClass>;
        "chatbot.script.answer": StaticMailRecord<ChatbotScriptStepAnswer, typeof ChatbotScriptStepAnswerClass>;
        "chatbot.script.step": StaticMailRecord<ChatbotScriptStep, typeof ChatbotScriptStepClass>;
        ChatbotStep: StaticMailRecord<ChatbotStep, typeof ChatbotStepClass>;
        has_access_livechat: boolean;
        "im_livechat.channel": StaticMailRecord<LivechatChannel, typeof LivechatChannelClass>;
        "im_livechat.channel.member.history": StaticMailRecord<LivechatChannelMemberHistory, typeof LivechatChannelMemberHistoryClass>;
        "im_livechat.channel.rule": StaticMailRecord<LivechatChannelRule, typeof LivechatChannelRuleClass>;
        "im_livechat.expertise": StaticMailRecord<LivechatExpertise, typeof LivechatExpertiseClass>;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@im_livechat/core/common/thread_model_patch").threadPatch> {}
    export interface Models {
        Chatbot: Chatbot;
        "chatbot.message": ChatbotMessage;
        "chatbot.script": ChatbotScript;
        "chatbot.script.answer": ChatbotScriptStepAnswer;
        "chatbot.script.step": ChatbotScriptStep;
        ChatbotStep: ChatbotStep;
        "im_livechat.channel": LivechatChannel;
        "im_livechat.channel.member.history": LivechatChannelMemberHistory;
        "im_livechat.channel.rule": LivechatChannelRule;
        "im_livechat.expertise": LivechatExpertise;
    }
}
