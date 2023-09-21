declare module "models" {

    import { Message } from "models"

    export interface Message {
        pinnedAt: string,
    }

    export interface Thread {
        pinnedMessages: Set<Message>,
        pinnedMessagesState: "loaded"|"loading"|"error"|undefined,
    }

}
