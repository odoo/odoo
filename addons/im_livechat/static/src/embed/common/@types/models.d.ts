declare module "models" {
    export interface Thread {
        chatbotTypingMessage: Message,
        livechatWelcomeMessage: Message,
        chatbot_script_id: number | null,
        requested_by_operator: boolean,
    }
}
