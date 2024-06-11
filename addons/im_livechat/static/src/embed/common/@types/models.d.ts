declare module "models" {
    export interface Thread {
        chatbotTypingMessage: Message,
        livechatWelcomeMessage: Message,
        chatbotScriptId: number | null,
        isNewlyCreated: boolean,
    }
}
