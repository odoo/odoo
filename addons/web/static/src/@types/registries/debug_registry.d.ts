declare module "registries" {
    import { Component, ComponentConstructor } from "@odoo/owl";
    import { OdooEnv } from "@web/env";

    interface AccessRights {
        canEditView: boolean;
        canSeeAccesses: boolean;
    }

    interface DebugRegistryItemShapeParams {
        accessRights: AccessRights;
        env: OdooEnv;
        [k: string]: any;
    }

    interface DebugComponent {
        type: "component";
        Component: ComponentConstructor;
        props: object;
        sequence?: number;
        section?: string;
    }

    interface DebugItem {
        type: "item";
        callback?: () => void | Promise<void>;
        description: string;
        href?: string;
        sequence?: number;
        section?: string;
    }

    type DebugRegistryItemShapeResult = DebugComponent | DebugItem | null | false | undefined;

    export type DebugRegistryItemShape = (
        params: DebugRegistryItemShapeParams,
    ) => DebugRegistryItemShapeResult;

    export type DebugRegistryCategories = Record<string, DebugRegistryItemShape>;

    export interface DebugSectionRegistryItemShape {
        label: string;
        sequence?: number;
    }

    interface GlobalRegistryCategories {
        debug: RegistryData<DebugRegistryItemShape, DebugRegistryCategories>;
        debug_section: DebugSectionRegistryItemShape;
    }
}
