declare module "models" {
    export interface Message {
        messagingMenuTabsAsMessage: MessagingMenuTab[];
    }
    export interface Store {
        action_discuss_id: number|undefined;
        discuss: DiscussApp;
        messagingMenu: MessagingMenu;
    }
    export interface Thread {
        askLeaveConfirmation: (body: string) => Promise<void>;
        discussAppAsThread: DiscussApp;
        setActiveURL: () => void;
        setAsDiscussThread: (pushState: boolean) => void;
    }
}
