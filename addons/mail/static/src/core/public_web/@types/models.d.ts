declare module "models" {
    export interface Store {
        action_discuss_id: number|undefined;
        discuss: DiscussApp;
        menuThreads: Thread[];
    }
    export interface Thread {
        askLeaveConfirmation: (body: string) => Promise<void>;
        autoOpenChatWindowOnNewMessage: Readonly<boolean>;
        discussAppAsThread: DiscussApp;
        inChathubOnNewMessage: Readonly<boolean>;
        setActiveURL: () => void;
        setAsDiscussThread: (pushState: boolean) => void;
        unpin: () => Promise<void>;
    }
}
