declare module "fields" {
    import { DomainListRepr } from "@web/core/domain";

    interface IFieldDefinition<T extends FieldType> {
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
        aggregator:
            | "array_agg"
            | "avg"
            | "bool_and"
            | "bool_or"
            | "count"
            | "count_distinct"
            | "max"
            | "min"
            | "sum";
    }

    interface ITextual {
        translate: boolean;
    }

    // ------------------------------------------------------------------------

    export type BinaryFieldDefinition = IFieldDefinition<"binary">;

    export type BooleanFieldDefinition = IFieldDefinition<"boolean">;

    export type CharFieldDefinition = IFieldDefinition<"char"> &
        ITextual & {
            size?: number;
            trim: boolean;
        };

    export type DateFieldDefinition = IFieldDefinition<"date">;

    export type DateTimeFieldDefinition = IFieldDefinition<"datetime">;

    export type FloatFieldDefinition = IFieldDefinition<"float"> & INumerical;

    export type GenericFieldDefinition = IFieldDefinition<"generic">;

    export type HtmlFieldDefinition = IFieldDefinition<"html"> &
        ITextual & {
            sanitize: boolean;
            sanitize_tags: boolean;
        };

    export type ImageFieldDefinition = IFieldDefinition<"image">;

    export type IntegerFieldDefinition = IFieldDefinition<"integer"> & INumerical;

    export type JsonFieldDefinition = IFieldDefinition<"json">;

    export type Many2ManyFieldDefinition = IFieldDefinition<"many2many"> & IRelational;

    export type Many2OneFieldDefinition = IFieldDefinition<"many2one"> & IRelational;

    export type Many2OneReferenceFieldDefinition = IFieldDefinition<"many2one_reference">;

    export type MonetaryFieldDefinition = IFieldDefinition<"monetary"> &
        INumerical & {
            currency_field: string;
        };

    export type One2ManyFieldDefinition = IFieldDefinition<"one2many"> &
        IRelational & {
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

    export type FieldDefinitionsByType = {
        binary: BinaryFieldDefinition;
        boolean: BooleanFieldDefinition;
        char: CharFieldDefinition;
        date: DateFieldDefinition;
        datetime: DateTimeFieldDefinition;
        float: FloatFieldDefinition;
        generic: GenericFieldDefinition;
        html: HtmlFieldDefinition;
        image: ImageFieldDefinition;
        integer: IntegerFieldDefinition;
        json: JsonFieldDefinition;
        many2many: Many2ManyFieldDefinition;
        many2one_reference: Many2OneReferenceFieldDefinition;
        many2one: Many2OneFieldDefinition;
        monetary: MonetaryFieldDefinition;
        one2many: One2ManyFieldDefinition;
        properties_definition: PropertiesDefinitionFieldDefinition;
        properties: PropertiesFieldDefinition;
        reference: ReferenceFieldDefinition;
        selection: SelectionFieldDefinition;
        text: TextFieldDefinition;
    };

    export type FieldType = keyof FieldDefinitionsByType;

    export type FieldDefinition = FieldDefinitionsByType[FieldType];

    export type FieldDefinitionMap = Record<string, FieldDefinition>;
}
