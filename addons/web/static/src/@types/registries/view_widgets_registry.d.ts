declare module "registries" {
    import { Component } from "@odoo/owl";

    interface DynamicWidgetInfo {
        readonly: boolean;
    }

    interface StaticWidgetInfo {
        attrs: object;
        name: string;
        options: object;
        widget: ViewWidgetsRegistryItemShape;
    }

    export interface ViewWidgetsRegistryItemShape {
        additionalClasses?: string[];
        component: typeof Component;
        extractProps?(options: object, dynamicInfo: DynamicWidgetInfo): object;
        fieldDependencies?: Partial<StaticWidgetInfo>[] | ((baseInfo: StaticWidgetInfo) => Partial<StaticWidgetInfo>[]);
    }

    interface GlobalRegistryCategories {
        view_widgets: ViewWidgetsRegistryItemShape;
    }
}
