declare module "@web/env" {
    import { EventBus } from "@odoo/owl";
    import { ServiceFactories } from "services";

    export interface OdooEnv {
        bus: EventBus;
        debug: string;
        services: ServiceFactories;
        readonly isSmall: boolean;
        isReady: Promise<void>;
        config?: Record<string, any>;
        [key: string]: any;
    }

    export function makeEnv(): OdooEnv;
    export function startServices(env: OdooEnv): Promise<void>;
    export function mountComponent(
        component: import("@odoo/owl").Component,
        target: HTMLElement,
        appConfig?: Record<string, any>,
    ): Promise<import("@odoo/owl").App>;
}
