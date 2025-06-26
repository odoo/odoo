declare module "fields" {
    import { DomainListRepr } from "@web/core/domain";

    export type FieldType =
        "binary" |
        "boolean" |
        "char" |
        "date" |
        "datetime" |
        "float" |
        "html" |
        "image" |
        "integer" |
        "json" |
        "many2many" |
        "many2one" |
        "many2one_reference" |
        "monetary" |
        "one2many" |
        "properties" |
        "properties_definition" |
        "reference" |
        "selection" |
        "text";

    // ------------------------------------------------------------------------

    export interface IFieldDefinition<T extends FieldType> {
        change_default: boolean;
        groupable: boolean;
        groups?: string;
        help?: string;
        name: string;
        readonly: boolean;
        related?: string;
        required: boolean;
        searchable: boolean;
        sortable: boolean;
        store: boolean;
        string: string;
        type: T;
    }

    interface IRelational {
        context: string | object;
        domain: string | DomainListRepr;
        relation: string;
    }

    interface INumerical {
        aggregator: "array_agg" | "avg" | "bool_and" | "bool_or" | "count" | "count_distinct" | "max" | "min" | "sum";
    }

    interface ITextual {
        translate: boolean;
    }

    // ------------------------------------------------------------------------

    export type BinaryFieldDefinition = IFieldDefinition<"binary">;

    export type BooleanFieldDefinition = IFieldDefinition<"boolean">;

    export type CharFieldDefinition = IFieldDefinition<"char"> & ITextual & {
        size?: number;
        trim: boolean;
    };

    export type DateFieldDefinition = IFieldDefinition<"date">;

    export type DateTimeFieldDefinition = IFieldDefinition<"datetime">;

    export type FloatFieldDefinition = IFieldDefinition<"float"> & INumerical;

    export type HtmlFieldDefinition = IFieldDefinition<"html"> & ITextual & {
        sanitize: boolean;
        sanitize_tags: boolean;
    };

    export type ImageFieldDefinition = IFieldDefinition<"image">;

    export type IntegerFieldDefinition = IFieldDefinition<"integer"> & INumerical;

    export type JsonFieldDefinition = IFieldDefinition<"json">;

    export type Many2ManyFieldDefinition = IFieldDefinition<"many2many"> & IRelational;

    export type Many2OneFieldDefinition = IFieldDefinition<"many2one"> & IRelational;

    export type Many2OneReferenceFieldDefinition = IFieldDefinition<"many2one_reference">;

    export type MonetaryFieldDefinition = IFieldDefinition<"monetary"> & INumerical & {
        currency_field: string;
    };

    export type One2ManyFieldDefinition = IFieldDefinition<"one2many"> & IRelational & {
        relation_field: string;
    };

    export type PropertiesFieldDefinition = IFieldDefinition<"properties"> & {
        definition_record: string;
        definition_record_field: string;
    };

    export type PropertiesDefinitionFieldDefinition = IFieldDefinition<"properties_definition">;

    export type ReferenceFieldDefinition = IFieldDefinition<"reference"> & {
        selection: [value: number | string, label: string][];
    };

    export type SelectionFieldDefinition = IFieldDefinition<"selection"> & {
        selection: [value: number | string, label: string][];
    };

    export type TextFieldDefinition = IFieldDefinition<"text"> & ITextual;

    // ------------------------------------------------------------------------

    export type FieldDefinition =
        BinaryFieldDefinition |
        BooleanFieldDefinition |
        CharFieldDefinition |
        DateFieldDefinition |
        DateTimeFieldDefinition |
        FloatFieldDefinition |
        HtmlFieldDefinition |
        ImageFieldDefinition |
        IntegerFieldDefinition |
        JsonFieldDefinition |
        Many2ManyFieldDefinition |
        Many2OneFieldDefinition |
        Many2OneReferenceFieldDefinition |
        MonetaryFieldDefinition |
        One2ManyFieldDefinition |
        PropertiesFieldDefinition |
        PropertiesDefinitionFieldDefinition |
        ReferenceFieldDefinition |
        SelectionFieldDefinition |
        TextFieldDefinition;

    export type FieldDefinitionMap = Record<string, FieldDefinition>;
}
