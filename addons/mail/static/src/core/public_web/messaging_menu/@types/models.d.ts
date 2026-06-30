declare module "models" {
    import { MessagingMenu as MessagingMenuClass } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
    import { MessagingMenuState as MessagingMenuStateClass } from "@mail/core/public_web/messaging_menu/messaging_menu_state_model";
    import { MessagingMenuTab as MessagingMenuTabClass } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";

    export interface MessagingMenu extends MessagingMenuClass {}
    export interface MessagingMenuState extends MessagingMenuStateClass {}
    export interface MessagingMenuTab extends MessagingMenuTabClass {}

    export interface Store {
        MessagingMenu: StaticMailRecord<MessagingMenu, typeof MessagingMenuClass>;
        MessagingMenuState: StaticMailRecord<MessagingMenuState, typeof MessagingMenuStateClass>;
        MessagingMenuTab: StaticMailRecord<MessagingMenuTab, typeof MessagingMenuTabClass>;
    }

    export interface Models {
        MessagingMenu: MessagingMenu;
        MessagingMenuState: MessagingMenuState;
        MessagingMenuTab: MessagingMenuTab;
    }
}
