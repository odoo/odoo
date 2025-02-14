declare module "models" {
    import { LivechatRule as LivechatRuleClass } from "@im_livechat/embed/common/livechat_rule_model";

    export interface LivechatRule extends LivechatRuleClass {}

    export interface Thread {
        _startChatbot: boolean;
        chatbot: Chatbot;
        chatbotTypingMessage: Message;
        hasWelcomeMessage: Readonly<boolean>;
        isLastMessageFromCustomer: Readonly<unknown>;
        livechatWelcomeMessage: Message;
        requested_by_operator: boolean;
    }
    export interface Store {
        LivechatRule: LivechatRule;
    }

    export interface Models {
        LivechatRule: LivechatRule;
    }
}
