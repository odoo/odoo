declare module "registries" {
    import { Component } from "@odoo/owl";
    import { Interaction } from "@web/public/interaction";
    import { Compiler } from "@web/views/view_compiler";
    import { ActionDescription, ActionOptions } from "@web/webclient/actions/action_plugin";

    export type ActionHandlersRegistryItemShape = (action: ActionDescription, options: ActionOptions) => (void | Promise<void>);

    export type ActionsRegistryItemShape = (((action: ActionDescription) => void) | typeof Component) & {
        displayName?: string;
        path?: string;
        target?: ActionMode;
    };

    export interface CogMenuRegistryItemShape {
        Component: typeof Component;
        groupNumber: number;
        isDisplayed?: () => boolean;
    }

    export type DialogsRegistryItemShape = typeof Component;

    export type EffectsRegistryItemShape = (params: object) => ({ Component: typeof Component, props: object } | undefined);

    export type ErrorDialogsRegistryItemShape = typeof Component;

    export type ErrorHandler = (info: { error: Error, originalError: Error }) => boolean | void;

    export interface FavoriteMenuRegistryItemShape {
        Component: typeof Component;
        groupNumber: number;
        isDisplayed?(): boolean;
    }

    export type FormattersRegistryItemShape = (value: any) => any;

    export type FormCompilersRegistryItemShape = Compiler;

    interface KanbanHeaderConfigItemsFnParams {
        permissions: {
            canArchiveGroup: boolean;
            canDeleteGroup: boolean;
            canEditGroup: boolean;
        };
        props: object;
    }
    export interface GroupConfigItemsRegistryItemShape {
        label: TranslatedString;
        method: string | (() => {});
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
        isDisplayed?(): boolean;
    }

    export type IrActionsReportHandlers = (action: ActionRequest, options: ActionOptions) => (void | boolean | Promise<void | boolean>);

    export type InteractionRegistryItemShape = typeof Interaction;

    interface GlobalRegistryCategories {
        action_handlers: ActionHandlersRegistryItemShape;
        actions: ActionsRegistryItemShape;
        cogMenu: CogMenuRegistryItemShape;
        dialogs: DialogsRegistryItemShape;
        effetcs: EffectsRegistryItemShape;
        error_dialogs: ErrorDialogsRegistryItemShape;
        error_handlers: ErrorHandler;
        favoriteMenu: FavoriteMenuRegistryItemShape;
        formatters: FormattersRegistryItemShape;
        form_compilers: FormCompilersRegistryItemShape;
        group_config_items: GroupConfigItemsRegistryItemShape;
        lazy_components: LazyComponentsRegistryItemShape;
        main_components: MainComponentsRegistryItemShape;
        parsers: ParsersRegistryItemShape;
        public_components: PublicComponentsRegistryItemShape;
        "public.interactions": InteractionRegistryItemShape;
        sample_server: SampleServerRegistryItemShape;
        systray: SystrayRegistryItemShape;
        "ir.actions.report handlers": IrActionsReportHandlers;
    }
}
