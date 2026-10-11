declare module "models" {
    export interface Message {
        messagingMenuTabsAsMessages: MessagingMenuTab[];
    }
    export interface Store {
        discuss: DiscussApp;
        messagingMenu: MessagingMenu;
        showPushPermissionRequest: boolean;
    }
    export interface Thread {
        discussAppAsThread: DiscussApp;
    }
}
