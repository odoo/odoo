/**
 * Type declarations for the webclient module (`@web/webclient/`).
 *
 * Covers action management (action service, breadcrumbs, action info builders),
 * menu navigation, company switching, and the root WebClient component.
 */

// ---------------------------------------------------------------------------
// Action types
// ---------------------------------------------------------------------------

declare module "@web/webclient/actions/action_service" {
    import { Component, EventBus } from "@odoo/owl";

    export type ActionId = number | false;
    export type ActionMode = "current" | "fullscreen" | "new" | "main" | "self";
    export type ActionXMLId = string;
    export type ActionTag = string;
    export type ViewType = string;

    export interface ActionDescription {
        id?: ActionId;
        type: string;
        name?: string;
        display_name?: string;
        res_model?: string;
        res_id?: number | false;
        domain?: any[];
        context?: Record<string, any>;
        target?: ActionMode;
        views?: [number | false, string][];
        view_mode?: string;
        xml_id?: string;
        tag?: string;
        help?: string;
        [key: string]: any;
    }

    export type ActionRequest = ActionId | ActionXMLId | ActionTag | ActionDescription;

    export interface ActionOptions {
        additionalContext?: Record<string, any>;
        clearBreadcrumbs?: boolean;
        onClose?: (...args: any[]) => any;
        props?: Record<string, any>;
        viewType?: ViewType;
        stackPosition?: "replaceCurrentAction" | "replacePreviousAction";
        index?: number;
        newWindow?: boolean;
        forceLeave?: boolean;
        newStack?: any[];
        noEmptyTransition?: boolean;
        onActionReady?: (action: ActionDescription) => void;
    }

    export interface Controller {
        jsId: string;
        Component: typeof Component;
        action: ActionDescription;
        props: Record<string, any>;
        config: Record<string, any>;
        displayName: string;
        state: Record<string, any>;
        currentState: Record<string, any>;
        virtual?: boolean;
        lazy?: boolean;
        isMounted?: boolean;
    }

    export interface ActionService {
        doAction(
            actionRequest: ActionRequest,
            options?: ActionOptions,
        ): Promise<any>;
        loadAction(
            actionRequest: ActionRequest,
            context?: Record<string, any>,
        ): Promise<ActionDescription>;
        switchView(viewType: ViewType, props?: Record<string, any>): void;
        restore(jsId?: string): void;
        currentController: Controller | null;
    }

    export function clearUncommittedChanges(
        env: any,
        options?: { forceLeave?: boolean },
    ): Promise<void>;

    export const actionService: {
        dependencies: string[];
        start(env: any, services: Record<string, any>): ActionService;
    };
}

declare module "@web/webclient/actions/action_info_builders" {
    export interface ControllerInfo {
        props: Record<string, any>;
        currentState: Record<string, any>;
        config: Record<string, any>;
        displayName: string;
    }

    export function buildActionInfo(
        action: Record<string, any>,
        props: Record<string, any>,
        callbacks: { pushState: () => void },
    ): ControllerInfo;

    export function buildViewInfo(
        view: Record<string, any>,
        action: Record<string, any>,
        views: Record<string, any>[],
        props?: Record<string, any>,
        callbacks?: {
            getView: (type: string) => any;
            switchView: (type: string, props?: any, options?: any) => any;
            doAction: (action: any, options?: any) => any;
            pushState: () => void;
        },
    ): ControllerInfo;

    export function buildActionViews(
        action: Record<string, any>,
    ): Array<{
        icon: string;
        display_name: string;
        multiRecord: boolean;
        type: string;
    }>;
}

declare module "@web/webclient/actions/breadcrumb_manager" {
    export interface BreadcrumbItem {
        jsId: string;
        readonly name: string;
        readonly isFormView: boolean;
        readonly url: string;
        onSelected(): void;
    }

    export function buildBreadcrumbs(
        stack: Record<string, any>[],
        callbacks: {
            stateToUrl: (state: Record<string, any>) => string;
            restore: (jsId: string) => void;
        },
    ): BreadcrumbItem[];

    export function controllersFromState(
        state: Record<string, any>,
        ctx: {
            sessionStorage: Storage;
            stateToUrl: (state: Record<string, any>) => string;
            makeController: (params: Record<string, any>) => any;
            actionRegistry: any;
            breadcrumbCache: Record<string, any>;
        },
    ): Promise<Record<string, any>[]>;
}

declare module "@web/webclient/actions/action_state" {
    export function getActionParams(state: Record<string, any>): Record<string, any>;
    export function makeActionState(controller: Record<string, any>): Record<string, any>;
}

declare module "@web/webclient/actions/action_views" {
    export function findView(views: any[], viewType: string): any;
    export function getActionMode(action: Record<string, any>): string;
}

declare module "@web/webclient/actions/action_constants" {
    export const DIALOG_SIZES: Record<string, string>;
}

declare module "@web/webclient/actions/action_dialog" {
    import { Component } from "@odoo/owl";
    export class ActionDialog extends Component {}
}

declare module "@web/webclient/actions/action_container" {
    import { Component } from "@odoo/owl";
    export class ActionContainer extends Component {}
}

declare module "@web/webclient/actions/skeleton_view" {
    import { Component } from "@odoo/owl";
    export class SkeletonView extends Component {}
}

declare module "@web/webclient/actions/action_button_executor" {
    export function executeActionButton(
        env: any,
        clickParams: Record<string, any>,
        record: any,
    ): Promise<void>;
}

declare module "@web/webclient/actions/client_actions" {
    export function displayNotificationAction(env: any, action: any): void;
}

declare module "@web/webclient/actions/reports/report_executor" {
    export function executeReportAction(
        action: Record<string, any>,
        options: Record<string, any>,
        env: any,
    ): Promise<void>;
}

declare module "@web/webclient/actions/reports/report_hook" {
    export function useReportActions(): {
        print: () => Promise<void>;
    };
}

declare module "@web/webclient/actions/reports/utils" {
    export function buildReportUrl(action: Record<string, any>): string;
}

// ---------------------------------------------------------------------------
// Menu types
// ---------------------------------------------------------------------------

declare module "@web/webclient/menus/menu_service" {
    export interface MenuItem {
        id: number | string;
        name: string;
        children: (number | string)[];
        childrenTree?: MenuItem[];
        actionID?: number | false;
        appID?: number;
        xmlid?: string;
        webIconData?: string;
        webIcon?: string;
        [key: string]: any;
    }

    export interface MenuService {
        getAll(): MenuItem[];
        getApps(): MenuItem[];
        getMenu(menuId: number | string): MenuItem;
        getCurrentApp(): MenuItem | undefined;
        getMenuAsTree(menuId: number | string): MenuItem;
        selectMenu(menu: MenuItem | number): Promise<void>;
        setCurrentMenu(menu: MenuItem | number): void;
        reload(): Promise<void>;
    }

    export const menuService: {
        dependencies: string[];
        start(env: any): Promise<MenuService>;
    };
}

declare module "@web/webclient/menus/menu_providers" {
    import { Component } from "@odoo/owl";
    export class AppIconCommand extends Component {}
}

declare module "@web/webclient/menus/menu_helpers" {
    import type { MenuItem } from "@web/webclient/menus/menu_service";
    export function reorderApps(
        apps: MenuItem[],
        appIdOrder: (number | string)[],
    ): MenuItem[];
}

// ---------------------------------------------------------------------------
// Company switching
// ---------------------------------------------------------------------------

declare module "@web/webclient/switch_company_menu/switch_company_menu" {
    import { Component } from "@odoo/owl";
    export class SwitchCompanyMenu extends Component {}
}

declare module "@web/webclient/switch_company_menu/switch_company_item" {
    import { Component } from "@odoo/owl";
    export class SwitchCompanyItem extends Component {}
}

// ---------------------------------------------------------------------------
// Navbar and burger menu
// ---------------------------------------------------------------------------

declare module "@web/webclient/navbar/navbar" {
    import { Component } from "@odoo/owl";
    export class NavBar extends Component {}
}

declare module "@web/webclient/burger_menu/burger_user_menu/burger_user_menu" {
    import { Component } from "@odoo/owl";
    export class BurgerUserMenu extends Component {}
}

declare module "@web/webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu" {
    import { Component } from "@odoo/owl";
    export class MobileSwitchCompanyMenu extends Component {}
}

// ---------------------------------------------------------------------------
// User menu
// ---------------------------------------------------------------------------

declare module "@web/webclient/user_menu/user_menu" {
    import { Component } from "@odoo/owl";
    export class UserMenu extends Component {}
}

// ---------------------------------------------------------------------------
// Settings form view
// ---------------------------------------------------------------------------

declare module "@web/views/settings/settings_form_view" {
    export const SettingsFormView: Record<string, any>;
}

declare module "@web/views/settings/settings/settings_page" {
    import { Component } from "@odoo/owl";
    export class SettingsPage extends Component {}
}

declare module "@web/views/settings/settings/settings_app" {
    import { Component } from "@odoo/owl";
    export class SettingsApp extends Component {}
}

declare module "@web/views/settings/settings/settings_block" {
    import { Component } from "@odoo/owl";
    export class SettingsBlock extends Component {}
}

declare module "@web/views/settings/settings/searchable_setting" {
    import { Component } from "@odoo/owl";
    export class SearchableSetting extends Component {}
}

declare module "@web/views/settings/settings/highlight_text" {
    import { Component } from "@odoo/owl";
    export class HighlightText extends Component {}
}

// ---------------------------------------------------------------------------
// Debug / Profiling
// ---------------------------------------------------------------------------

declare module "@web/webclient/debug/profiling/profiling_service" {
    export interface ProfilingState {
        session: string | false;
        collectors: string[];
        params: Record<string, any>;
        readonly isEnabled: boolean;
    }

    export interface ProfilingService {
        state: ProfilingState;
        toggleProfiling(): Promise<void>;
        toggleCollector(collector: string): Promise<void>;
        setParam(key: string, value: any): Promise<void>;
        isCollectorEnabled(collector: string): boolean;
    }

    export const profilingService: {
        dependencies: string[];
        start(env: any, services: Record<string, any>): ProfilingService | undefined;
    };
}

// ---------------------------------------------------------------------------
// Other webclient services
// ---------------------------------------------------------------------------

declare module "@web/webclient/currency_service" {
    export const currencyService: {
        dependencies: string[];
        start(env: any, services: Record<string, any>): void;
    };
}

declare module "@web/webclient/session_service" {
    export const lazySession: {
        start(): Promise<void>;
    };
}

declare module "@web/webclient/density/density_service" {
    export const densityService: {
        start(): void;
    };
}

declare module "@web/views/settings/widgets/demo_data_service" {
    export const demoDataService: {
        start(): Promise<{
            isDemoDataActive(): Promise<boolean>;
        }>;
    };
}

declare module "@web/views/settings/widgets/user_invite_service" {
    export const userInviteService: {
        start(): Promise<{
            fetchData(reload?: boolean): Promise<any>;
        }>;
    };
}

declare module "@web/webclient/share_target/share_target_service" {
    export const shareTargetService: {
        start(): void;
    };
}

// ---------------------------------------------------------------------------
// WebClient root component
// ---------------------------------------------------------------------------

declare module "@web/webclient/webclient" {
    import { Component } from "@odoo/owl";
    export class WebClient extends Component {}
}
