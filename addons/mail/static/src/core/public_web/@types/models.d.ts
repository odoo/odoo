declare module "models" {
    export interface Message {
        messagingMenuTabsAsMessages: MessagingMenuTab[];
    }
    export interface Store {
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
