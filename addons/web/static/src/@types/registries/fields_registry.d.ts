declare module "registries" {
    import { FieldDefinition, FieldType } from "fields";
    import { Component } from "@odoo/owl";
    import { Domain } from "@web/core/domain";
    import { _t } from "@web/core/l10n/translation";

    type TranslatableString = ReturnType<typeof _t> | string;

    interface DynamicFieldInfo {
        context: Record<string, any>;
        domain(): Domain | undefined;
        readonly: boolean;
    }

    interface StaticFieldInfo {
        attrs: Record<string, any>;
        context: string;
        decorations: Record<string, any>;
        domain?: string;
        field: FieldDefinition;
        forceSave: boolean;
        help?: TranslatableString;
        name: string;
        onChange: boolean;
        options: Record<string, any>;
        string: TranslatableString;
        type: string;
        viewType: string;
        widget?: string;
    }

    type OptionType = "boolean" | "field" | "number" | "selection" | "string";

    interface IOption<T extends OptionType> {
        help?: TranslatableString;
        label: TranslatableString;
        name: string;
        type: T;
    }

    interface BooleanOption extends IOption<"boolean"> {
        default?: boolean;
    }

    interface FieldOption extends IOption<"field"> {
        availableTypes?: FieldType[];
    }

    interface NumberOption extends IOption<"number"> {
        default?: number;
    }

    interface StringOption extends IOption<"string"> {
        default?: string;
    }

    interface SelectionOptionChoice {
        label: TranslatableString;
        value: string;
    }

    interface SelectionOption extends IOption<"selection"> {
        choices: SelectionOptionChoice[];
        default?: string;
    }

    type SupportedOptions = BooleanOption | FieldOption | NumberOption | SelectionOption | StringOption;

    export interface FieldsRegistryItemShape {
        additionalClasses?: string[];
        component: any;
        displayName?: TranslatableString;
        extractProps?(...args: any[]): Record<string, any>;
        fieldDependencies?: Partial<StaticFieldInfo>[] | ((baseInfo: StaticFieldInfo) => Partial<StaticFieldInfo>[]);
        listViewWidth?: number | number[] | ((param: { type: string; hasLabel: boolean; }) => number | false);
        relatedFields?: Partial<StaticFieldInfo>[] | ((baseInfo: StaticFieldInfo) => Partial<StaticFieldInfo>[]);
        isEmpty?(...args: any[]): boolean;
        supportedAttributes?: any[];
        supportedOptions?: any[];
        supportedTypes?: string[];
        useSubView?: boolean;
        [key: string]: any;
    }

    interface GlobalRegistryCategories {
        fields: FieldsRegistryItemShape;
    }
}
