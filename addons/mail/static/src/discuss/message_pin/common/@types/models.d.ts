declare module "models" {
    export interface Message {
        pin: () => Deferred<boolean>;
        pinned_at: import("luxon").DateTime;
        unpin: () => Deferred<boolean>;
    }
    export interface Thread {
        fetchPinnedMessages: () => Promise<void>;
        pinnedMessages: Message[];
        pinnedMessagesState: 'loaded'|'loading'|'error'|undefined;
    }
}
