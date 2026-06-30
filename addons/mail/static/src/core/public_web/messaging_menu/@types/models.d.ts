declare module "models" {
    import { MessagingMenu as MessagingMenuClass } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
    import { MessagingMenuTab as MessagingMenuTabClass } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";
    import { MessagingMenuUIState as MessagingMenuUIStateClass } from "@mail/core/public_web/messaging_menu/messaging_menu_ui_state_model";

    export interface MessagingMenu extends MessagingMenuClass {}
    export interface MessagingMenuTab extends MessagingMenuTabClass {}
    export interface MessagingMenuUIState extends MessagingMenuUIStateClass {}

    export interface Store {
        MessagingMenu: StaticMailRecord<MessagingMenu, typeof MessagingMenuClass>;
        MessagingMenuTab: StaticMailRecord<MessagingMenuTab, typeof MessagingMenuTabClass>;
        MessagingMenuUIState: StaticMailRecord<MessagingMenuUIState, typeof MessagingMenuUIStateClass>;
    }

    export interface Models {
        MessagingMenu: MessagingMenu;
        MessagingMenuTab: MessagingMenuTab;
        MessagingMenuUIState: MessagingMenuUIState;
    }
}
