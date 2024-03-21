declare module "registries" {
    import { FieldDefinition, FieldType } from "fields";
    import { Component } from "@odoo/owl";
    import { Domain } from "@web/core/domain";

    interface DynamicFieldInfo {
        context: object;
        domain(): Domain | undefined;
        readonly: boolean;
    }

    interface StaticFieldInfo {
        attrs: object;
        context: string;
        decorations: object;
        domain?: string;
        field: FieldDefinition;
        forceSave: boolean;
        help?: string;
        name: string;
        onChange: boolean;
        options: object;
        string: string;
        type: string;
        viewType: string;
        widget?: string;
    }

    type OptionType = "boolean" | "field" | "number" | "selection" | "string";

    interface IOption<T extends OptionType> {
        help?: string;
        label: string;
        name: string;
        type: T;
    }

    interface BooleanOption extends IOption<"boolean"> {
        default?: boolean;
    }

    interface FieldOption extends IOption<"field"> {
        availableTypes: FieldType[];
    }

    interface NumberOption extends IOption<"number"> {
        default?: number;
    }

    interface StringOption extends IOption<"string"> {
        default?: string;
    }

    interface SelectionOptionChoice {
        label: string;
        value: string;
    }

    interface SelectionOption extends IOption<"selection"> {
        choices: SelectionOptionChoice[];
        default?: string;
    }

    type SupportedOptions = BooleanOption | FieldOption | NumberOption | SelectionOption | StringOption;

    export interface FieldsRegistryItemShape {
        additionalClasses?: string[];
        component: typeof Component;
        displayName?: string;
        extractProps?(options: StaticFieldInfo, dynamicInfo: DynamicFieldInfo): object;
        fieldDependencies?: Partial<StaticFieldInfo>[] | ((baseInfo: StaticFieldInfo) => Partial<StaticFieldInfo>[]);
        relatedFields?: Partial<StaticFieldInfo>[] | ((baseInfo: StaticFieldInfo) => Partial<StaticFieldInfo>[]);
        isEmpty?(record: object, fieldName: string): boolean;
        supportedOptions?: SupportedOptions[];
        supportedTypes?: FieldType[];
        useSubView?: boolean;
    }

    interface GlobalRegistryCategories {
        fields: FieldsRegistryItemShape;
    }
}
