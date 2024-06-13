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
    }

    interface DebugItem {
        type: "item";
        callback?: () => (void | Promise<void>);
        description: string;
        href?: string;
        sequence: number;
    }

    interface DebugSeparator {
        type: "separator";
        sequence: number;
    }

    type DebugRegistryItemShapeResult = DebugComponent | DebugItem | DebugSeparator | null;

    export type DebugRegistryItemShape = (params: DebugRegistryItemShapeParams) => DebugRegistryItemShapeResult;

    export type DebugRegistryCategories = Record<string, DebugRegistryItemShape>;

    interface GlobalRegistryCategories {
        debug: RegistryData<DebugRegistryItemShape, DebugRegistryCategories>;
    }
}
