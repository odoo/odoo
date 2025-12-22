declare module "registries" {
    import { Component } from "@odoo/owl";
    import { OdooEnv } from "@web/env";
    import { NotificationOptions } from "@web/core/notifications/notification_service";
    import { Compiler } from "@web/views/view_compiler";
    import { ActionDescription } from "@web/webclient/actions/action_service";

    interface ActionHandlerParams {
        action: object;
        env: OdooEnv;
        options: ActionOptions;
    }
    export type ActionHandlersRegistryItemShape = (params: ActionHandlerParams) => (void | Promise<void>);

    export type ActionsRegistryItemShape = (((env: OdooEnv, action: ActionDescription) => void) | typeof Component) & {
        displayName?: string;
        path?: string;
        target?: ActionMode;
    };

    export interface CogMenuRegistryItemShape {
        Component: typeof Component;
        groupNumber: number;
        isDisplayed?: (env: OdooEnv) => boolean;
    }

    export type DialogsRegistryItemShape = typeof Component;

    export type EffectsRegistryItemShape = (env: OdooEnv, params: object) => ({ Component: typeof Component, props: object } | undefined);

    export type ErrorDialogsRegistryItemShape = typeof Component;

    export type ErrorHandlersRegistryItemShape = (env: OdooEnv, error: Error, originalError: Error) => boolean;

    export type ErrorNotificationsRegistryItemShape = NotificationOptions & { message?: string };

    export interface FavoriteMenuRegistryItemShape {
        Component: typeof Component;
        groupNumber: number;
        isDisplayed?: (env: OdooEnv) => boolean;
    }

    export type FormattersRegistryItemShape = (value: any) => any;

    export type FormCompilersRegistryItemShape = Compiler;

    interface KanbanHeaderConfigItemsFnParams {
        permissions: {
            canArchiveGroup: boolean;
            canDeleteGroup: boolean;
            canEditGroup: boolean;
            canQuickCreate: boolean;
        };
        props: object;
    }
    export interface KanbanHeaderConfigItemsRegistryItemShape {
        label: String;
        method: string;
        isVisible: boolean | ((params: KanbanHeaderConfigItemsFnParams) => boolean);
        class: string | ((params: KanbanHeaderConfigItemsFnParams) => (string | string[] | { [key: string]: boolean }));
    }

    export type LazyComponentsRegistryItemShape = typeof Component;

    export interface MainComponentsRegistryItemShape {
        component: typeof Component;
        props?: object;
    }

    export type ParsersRegistryItemShape = (value: any) => any;

    export type PublicComponentsRegistryItemShape = typeof Component;

    export type SampleServerRegistryItemShape = (...args: any[]) => any;

    export interface SystrayRegistryItemShape {
        Component: typeof Component;
        isDisplayed?: (env: OdooEnv) => boolean;
    }

    export type IrActionsReportHandlers = (action: ActionRequest, options: ActionOptions, env: OdooEnv) => (void | boolean | Promise<void | boolean>);

    interface GlobalRegistryCategories {
        action_handlers: ActionHandlersRegistryItemShape;
        actions: ActionsRegistryItemShape;
        cogMenu: CogMenuRegistryItemShape;
        dialogs: DialogsRegistryItemShape;
        effetcs: EffectsRegistryItemShape;
        error_dialogs: ErrorDialogsRegistryItemShape;
        error_handlers: ErrorHandlersRegistryItemShape;
        error_notifications: ErrorNotificationsRegistryItemShape;
        favoriteMenu: FavoriteMenuRegistryItemShape;
        formatters: FormattersRegistryItemShape;
        form_compilers: FormCompilersRegistryItemShape;
        kanban_header_config_items: KanbanHeaderConfigItemsRegistryItemShape;
        lazy_components: LazyComponentsRegistryItemShape;
        main_components: MainComponentsRegistryItemShape;
        parsers: ParsersRegistryItemShape;
        public_components: PublicComponentsRegistryItemShape;
        sample_server: SampleServerRegistryItemShape;
        systray: SystrayRegistryItemShape;
        "ir.actions.report handlers": IrActionsReportHandlers;
    }
}
