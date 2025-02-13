declare module "models" {
    export interface Message {
        pin: () => unknown;
        pinned_at: luxon.DateTime;
        unpin: () => unknown;
    }
    export interface Thread {
        fetchPinnedMessages: () => Promise<undefined>;
        pinnedMessages: Message[];
        pinnedMessagesState: unknown;
    }
}
