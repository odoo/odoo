declare module "registries" {
    import { FieldDefinitionMap } from "fields";
    import { Component } from "@odoo/owl";
    import { Model } from "@web/model/model";
    import { SearchModel } from "@web/search/search_model";
    import { ViewCompiler } from "@web/views/view_compiler";

    interface ArchParser {
        parse(xmlDoc: XMLDocument, models: Record<string, FieldDefinitionMap>, modelName: string): any;
    }

    interface ViewInfo {
        arch: string;
        className: string;
        fields: FieldDefinitionMap;
        globalState?: object;
        info: object;
        relatedModels: Record<string, FieldDefinitionMap>;
        resModel: string;
        searchMenuTypes: string[];
        state?: object;
        useSampleModel: boolean;
    }

    export interface ViewsRegistryItemShape {
        ArchParser: ArchParser;
        buttonTemplate?: string;
        Controller: typeof Component;
        Compiler?: typeof ViewCompiler;
        Model: typeof Model;
        props(genericProps: ViewInfo, viewDescr: ViewsRegistryItemShape, config: object): object;
        Renderer: typeof Component;
        searchMenuTypes?: ("filter" | "groupBy" | "comparison" | "favorite")[];
        SearchModel?: typeof SearchModel;
        type: string;
    }

    interface GlobalRegistryCategories {
        views: ViewsRegistryItemShape;
    }
}
