declare module "models" {
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app_model";

    export interface DiscussApp extends DiscussAppClass {}

    export interface Store {
        DiscussApp: DiscussApp;
        discuss: DiscussApp;
    }
    export interface Thread {
        askLeaveConfirmation: (body: unknown) => object;
        autoOpenChatWindowOnNewMessage: Readonly<boolean>;
        leaveChannel: ({ force: boolean }) => Promise<void>;
        notifyMessageToUser: (message: Message) => Promise<void>;
        setActiveURL: () => void;
        setAsDiscussThread: (pushState: boolean) => void;
        unpin: () => Promise<unknown>;
    }

    export interface Models {
        DiscussApp: DiscussApp;
    }
}
