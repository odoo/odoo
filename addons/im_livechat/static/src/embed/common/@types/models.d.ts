declare module "models" {
    export interface DiscussChannel {
        hasActiveChatbot: Readonly<boolean>;
        hasWelcomeMessage: Readonly<boolean>;
        isLastCommentFromVisitor: Readonly<boolean>;
        livechatWelcomeMessage: Message;
        storeAsActiveVisitorLivechats: Store;
    }
    export interface Message {
        disableChatbotAnswers: boolean;
        isWelcomeMessage: boolean;
    }
    export interface Store {
        activeVisitorLivechats: DiscussChannel[];
        guest_token: string|null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        _prevComposerDisabled: boolean;
        readyToSwapPromise: Promise<void>;
        resolveReadyToSwap: (value: unknown) => void;
    }
}
