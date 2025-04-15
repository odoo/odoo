
declare module "models" {

    export interface Message {
        pinnedAt: string,
    }

    export interface Thread {
        pinnedMessages: Message[],
        pinnedMessagesState: "loaded"|"loading"|"error"|undefined,
    }

}
