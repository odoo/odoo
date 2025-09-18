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
        ArchParser?: any;
        buttonTemplate?: string;
        Controller?: any;
        Compiler?: any;
        Model?: any;
        props?(genericProps: ViewInfo, viewDescr: ViewsRegistryItemShape, config: object): object;
        Renderer?: any;
        searchMenuTypes?: string[];
        SearchModel?: any;
        type: string;
    }

    interface GlobalRegistryCategories {
        views: ViewsRegistryItemShape;
    }
}
