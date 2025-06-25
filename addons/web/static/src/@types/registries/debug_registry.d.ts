declare module "registries" {
    import { Component } from "@odoo/owl";
    import { OdooEnv } from "@web/env";

    interface AccessRights {
        canEditView: boolean;
        canSeeRecordRules: boolean;
        canSeeModelAccess: boolean;
    }

    interface DebugRegistryItemShapeParams {
        accessRights: AccessRights;
        env: OdooEnv;
        [k: string]: any;
    }

    interface DebugComponent {
        type: "component";
        Component: typeof Component;
        props: object;
        sequence: number;
        section?: string;
    }

    interface DebugItem {
        type: "item";
        callback?: () => (void | Promise<void>);
        description: string;
        href?: string;
        sequence: number;
        section?: string;
    }

    type DebugRegistryItemShapeResult = DebugComponent | DebugItem | null;

    export type DebugRegistryItemShape = (params: DebugRegistryItemShapeParams) => DebugRegistryItemShapeResult;

    export type DebugRegistryCategories = Record<string, DebugRegistryItemShape>;

    export interface DebugSectionRegistryItemShape {
        label: string;
        sequence: number;
    };

    interface GlobalRegistryCategories {
        debug: RegistryData<DebugRegistryItemShape, DebugRegistryCategories>;
        debug_section: DebugSectionRegistryItemShape;
    }
}
