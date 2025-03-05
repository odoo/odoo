/** @odoo-module */

/**
 * @typedef {object} ServerData
 * @property {object} models
 * @property {object} views
 */

/**
 * Get a basic arch for a pivot, which is compatible with the data given by
 * getBasicData().
 *
 * Here is the pivot created:
 *     A      B      C      D      E      F
 * 1          1      2      12     17     Total
 * 2          Proba  Proba  Proba  Proba  Proba
 * 3  false          15                    15
 * 4  true    11            10     95     116
 * 5  Total   11     15     10     95     131
 */
export function getBasicPivotArch() {
    return /* xml */ `
        <pivot string="Partners">
            <field name="foo" type="col"/>
            <field name="bar" type="row"/>
            <field name="probability" type="measure"/>
        </pivot>`;
}

/**
 * Get a basic arch for a list, which is compatible with the data given by
 * getBasicData().
 *
 * Here is the list created:
 *     A      B      C          D
 * 1  Foo     bar    Date       Product
 * 2  12      True   2016-04-14 xphone
 * 3  1       True   2016-10-26 xpad
 * 4  17      True   2016-12-15 xpad
 * 5  2       False  2016-12-11 xpad
 */
export function getBasicListArch() {
    return /* xml */ `
        <tree string="Partners">
            <field name="foo"/>
            <field name="bar"/>
            <field name="date"/>
            <field name="product_id"/>
        </tree>
    `;
}

export function getBasicGraphArch() {
    return /* xml */ `
        <graph>
            <field name="bar" />
        </graph>
    `;
}

/**
 * @returns {ServerData}
 */
export function getBasicServerData() {
    return {
        models: getBasicData(),
        views: {
            "partner,false,list": getBasicListArch(),
            "partner,false,pivot": getBasicPivotArch(),
            "partner,false,graph": getBasicGraphArch(),
            "partner,false,form": /* xml */ `<Form/>`,
            "partner,false,search": /* xml */ `<search/>`,
        },
    };
}

/**
 *
 * @param {string} model
 * @param {Array<string>} columns
 * @param {Object} data
 *
 * @returns { {definition: Object, columns: Array<Object>}}
 */
export function generateListDefinition(model, columns, data = getBasicData()) {
    const cols = [];
    for (const name of columns) {
        cols.push({
            name,
            type: data[model].fields[name].type,
        });
    }
    return {
        definition: {
            metaData: {
                resModel: model,
                columns,
            },
            searchParams: {
                domain: [],
                context: {},
                orderBy: [],
            },
            name: "List",
        },
        columns: cols,
    };
}

export function getBasicListArchs() {
    return {
        "partner,false,list": getBasicListArch(),
        "partner,false,search": /* xml */ `<search/>`,
        "partner,false,form": /* xml */ `<form/>`,
    };
}

export function getBasicData() {
    return {
        "documents.document": {
            fields: {
                name: { string: "Name", type: "char" },
                raw: { string: "Data", type: "text" },
                thumbnail: { string: "Thumbnail", type: "text" },
                display_thumbnail: { string: "Thumbnail", type: "text" },
                favorited_ids: { string: "Name", type: "many2many" },
                is_favorited: { string: "Name", type: "boolean" },
                mimetype: { string: "Mimetype", type: "char" },
                partner_id: { string: "Related partner", type: "many2one", relation: "partner" },
                owner_id: { string: "Owner", type: "many2one", relation: "partner" },
                handler: {
                    string: "Handler",
                    type: "selection",
                    selection: [["spreadsheet", "Spreadsheet"]],
                },
                previous_attachment_ids: {
                    string: "History",
                    type: "many2many",
                    relation: "ir.attachment",
                },
                tag_ids: { string: "Tags", type: "many2many", relation: "documents.tag" },
                folder_id: { string: "Workspaces", type: "many2one", relation: "documents.folder" },
                res_model: { string: "Model (technical)", type: "char" },
                available_rule_ids: {
                    string: "Rules",
                    type: "many2many",
                    relation: "documents.workflow.rule",
                },
            },
            records: [
                {
                    id: 1,
                    name: "My spreadsheet",
                    raw: "{}",
                    is_favorited: false,
                    folder_id: 1,
                    handler: "spreadsheet",
                },
                {
                    id: 2,
                    name: "",
                    raw: "{}",
                    is_favorited: true,
                    folder_id: 1,
                    handler: "spreadsheet",
                },
            ],
        },
        "ir.model": {
            fields: {
                name: { string: "Model Name", type: "char" },
                model: { string: "Model", type: "char" },
            },
            records: [
                {
                    id: 37,
                    name: "Product",
                    model: "product",
                },
                {
                    id: 40,
                    name: "Partner",
                    model: "partner",
                },
            ],
        },
        "documents.folder": {
            fields: {
                name: { string: "Name", type: "char" },
                parent_folder_id: {
                    string: "Parent Workspace",
                    type: "many2one",
                    relation: "documents.folder",
                },
                description: { string: "Description", type: "text" },
            },
            records: [
                {
                    id: 1,
                    name: "Workspace1",
                    description: "Workspace",
                    parent_folder_id: false,
                },
            ],
        },
        "documents.tag": {
            fields: {},
            records: [],
            get_tags: () => [],
        },
        "documents.workflow.rule": {
            fields: {},
            records: [],
        },
        "documents.share": {
            fields: {},
            records: [],
        },
        "spreadsheet.template": {
            fields: {
                name: { string: "Name", type: "char" },
                data: { string: "Data", type: "binary" },
                thumbnail: { string: "Thumbnail", type: "binary" },
                display_thumbnail: { string: "Thumbnail", type: "text" },
            },
            records: [
                { id: 1, name: "Template 1", data: btoa("{}") },
                { id: 2, name: "Template 2", data: btoa("{}") },
            ],
        },
        "res.currency": {
            fields: {
                name: { string: "Code", type: "char" },
                symbol: { string: "Symbol", type: "char" },
                position: {
                    string: "Position",
                    type: "selection",
                    selection: [
                        ["after", "A"],
                        ["before", "B"],
                    ],
                },
                decimal_places: { string: "decimal", type: "integer" },
            },
            records: [
                {
                    id: 1,
                    name: "EUR",
                    symbol: "€",
                    position: "after",
                    decimal_places: 2,
                },
                {
                    id: 2,
                    name: "USD",
                    symbol: "$",
                    position: "before",
                    decimal_places: 2,
                },
            ],
        },
        partner: {
            fields: {
                foo: {
                    string: "Foo",
                    type: "integer",
                    store: true,
                    searchable: true,
                    group_operator: "sum",
                },
                bar: {
                    string: "Bar",
                    type: "boolean",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                name: {
                    string: "name",
                    type: "char",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                date: {
                    string: "Date",
                    type: "date",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                create_date: {
                    string: "Creation Date",
                    type: "datetime",
                    store: true,
                    sortable: true,
                },
                active: { string: "Active", type: "bool", default: true, searchable: true },
                product_id: {
                    string: "Product",
                    type: "many2one",
                    relation: "product",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                tag_ids: {
                    string: "Tags",
                    type: "many2many",
                    relation: "tag",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                probability: {
                    string: "Probability",
                    type: "float",
                    searchable: true,
                    store: true,
                    group_operator: "avg",
                },
                field_with_array_agg: {
                    string: "field_with_array_agg",
                    type: "integer",
                    searchable: true,
                    group_operator: "array_agg",
                },
                currency_id: {
                    string: "Currency",
                    type: "many2one",
                    relation: "res.currency",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                pognon: {
                    string: "Money!",
                    type: "monetary",
                    currency_field: "currency_id",
                    store: true,
                    sortable: true,
                    group_operator: "avg",
                    searchable: true,
                },
                partner_properties: {
                    string: "Properties",
                    type: "properties",
                    store: true,
                    sortable: true,
                    searchable: true,
                },
                jsonField: {
                    string: "Json Field",
                    type: "json",
                    store: true,
                },
            },
            records: [
                {
                    id: 1,
                    foo: 12,
                    bar: true,
                    date: "2016-04-14",
                    create_date: "2016-04-03 00:00:00",
                    product_id: 37,
                    probability: 10,
                    field_with_array_agg: 1,
                    tag_ids: [42, 67],
                    currency_id: 1,
                    pognon: 74.4,
                },
                {
                    id: 2,
                    foo: 1,
                    bar: true,
                    date: "2016-10-26",
                    create_date: "2014-04-03 00:05:32",
                    product_id: 41,
                    probability: 11,
                    field_with_array_agg: 2,
                    tag_ids: [42, 67],
                    currency_id: 2,
                    pognon: 74.8,
                },
                {
                    id: 3,
                    foo: 17,
                    bar: true,
                    date: "2016-12-15",
                    create_date: "2006-01-03 11:30:50",
                    product_id: 41,
                    probability: 95,
                    field_with_array_agg: 3,
                    tag_ids: [],
                    currency_id: 1,
                    pognon: 4,
                },
                {
                    id: 4,
                    foo: 2,
                    bar: false,
                    date: "2016-12-11",
                    create_date: "2016-12-10 21:59:59",
                    product_id: 41,
                    probability: 15,
                    field_with_array_agg: 4,
                    tag_ids: [42],
                    currency_id: 2,
                    pognon: 1000,
                },
            ],
        },
        product: {
            fields: {
                name: { string: "Product Name", type: "char" },
                active: { string: "Active", type: "bool", default: true },
            },
            records: [
                {
                    id: 37,
                    display_name: "xphone",
                },
                {
                    id: 41,
                    display_name: "xpad",
                },
            ],
        },
        tag: {
            fields: {
                name: { string: "Tag Name", type: "char" },
            },
            records: [
                {
                    id: 42,
                    display_name: "isCool",
                },
                {
                    id: 67,
                    display_name: "Growing",
                },
            ],
        },
    };
}
