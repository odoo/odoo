declare module "models" {
    export interface DiscussChannel {
        hasWelcomeMessage: Readonly<boolean>;
        livechatWelcomeMessage: Message;
        storeAsActiveVisitorLivechats: Store;
    }
    export interface Message {
        isWelcomeMessage: boolean;
    }
    export interface Store {
        activeVisitorLivechats: DiscussChannel[];
        guest_token: string|null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        readyToSwapPromise: Promise<void>;
        resolveReadyToSwap: (value: unknown) => void;
    }
}
