declare module "models" {
    export interface DiscussChannel {
        hasWelcomeMessage: Readonly<boolean>;
        livechatWelcomeMessage: Message;
        storeAsActiveVisitorLivechats: Store;
    }
    export interface Store {
        activeVisitorLivechats: DiscussChannel[];
        guest_token: null;
        livechat_available: boolean;
        livechat_rule: LivechatChannelRule;
    }
    export interface Thread {
        readyToSwapPromise: Promise<void>;
        resolveReadyToSwap: (value: unknown) => void;
    }
}
