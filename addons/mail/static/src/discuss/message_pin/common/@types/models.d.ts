declare module "models" {

    export interface Message {
        pinned_at: string,
    }

    export interface Thread {
        pinnedMessages: Message[],
        pinnedMessagesState: "loaded"|"loading"|"error"|undefined,
    }

}
