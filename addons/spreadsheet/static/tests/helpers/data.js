import {
    MockServer,
    defineActions,
    defineModels,
    fields,
    models,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

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
 *
 * @returns { {definition: Object, columns: Array<Object>}}
 */
export function generateListDefinition(model, columns) {
    const cols = [];
    for (const name of columns) {
        const PyModel = Object.values(SpreadsheetModels).find((m) => m._name === model);
        cols.push({
            name,
            type: PyModel._fields[name].type,
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

export function defineSpreadsheetModels() {
    defineModels(SpreadsheetModels);
}

export function defineSpreadsheetActions() {
    defineActions([
        {
            id: 1,
            name: "partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            xml_id: "spreadsheet.partner_action",
            views: [
                [false, "list"],
                [false, "pivot"],
                [false, "graph"],
                [false, "search"],
                [false, "form"],
            ],
        },
    ]);
}

export class DocumentsDocument extends models.Model {
    _name = "documents.document";

    name = fields.Char({ string: "Name" });
    spreadsheet_data = fields.Binary({ string: "Data" });
    thumbnail = fields.Binary({ string: "Thumbnail" });
    favorited_ids = fields.Many2many({ string: "Name", relation: "res.users" });
    is_favorited = fields.Boolean({ string: "Name" });
    is_multipage = fields.Boolean({ string: "Is multipage" });
    mimetype = fields.Char({ string: "Mimetype" });
    partner_id = fields.Many2one({ string: "Related partner", relation: "partner" });
    owner_id = fields.Many2one({ string: "Owner", relation: "partner" });
    handler = fields.Selection({
        string: "Handler",
        selection: [["spreadsheet", "Spreadsheet"]],
    });
    previous_attachment_ids = fields.Many2many({
        string: "History",
        relation: "ir.attachment",
    });
    tag_ids = fields.Many2many({ string: "Tags", relation: "documents.tag" });
    folder_id = fields.Many2one({ string: "Workspaces", relation: "documents.folder" });
    res_model = fields.Char({ string: "Model (technical)" });
    available_rule_ids = fields.Many2many({
        string: "Rules",
        relation: "documents.workflow.rule",
    });

    _records = [
        {
            id: 1,
            name: "My spreadsheet",
            spreadsheet_data: "{}",
            is_favorited: false,
            folder_id: 1,
            handler: "spreadsheet",
        },
        {
            id: 2,
            name: "",
            spreadsheet_data: "{}",
            is_favorited: true,
            folder_id: 1,
            handler: "spreadsheet",
        },
    ];
}

export class IrModel extends webModels.IrModel {
    _records = [
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
        {
            id: 55,
            name: "Users",
            model: "res.users",
        },
    ];
}

export class IrUIMenu extends models.Model {
    _name = "ir.ui.menu";

    name = fields.Char({ string: "Name" });
    action = fields.Char({ string: "Action" });
    groups_id = fields.Many2many({ string: "Groups", relation: "res.group" });
}

export class IrActions extends models.Model {
    _name = "ir.actions";
}
export class ResGroup extends models.Model {
    _name = "res.group";
    name = fields.Char({ string: "Name" });
}

export class ResUsers extends mailModels.ResUsers {
    _name = "res.users";

    name = fields.Char({ string: "Name" });
    groups_id = fields.Many2many({ string: "Groups", relation: "res.group" });

    staticRecords = [
        {
            id: serverState.userId,
            active: true,
            company_id: serverState.companies[0]?.id,
            company_ids: serverState.companies.map((company) => company.id),
            login: "admin",
            partner_id: serverState.partnerId,
            password: "admin",
        },
    ];
}

export class DocumentsFolder extends models.Model {
    _name = "documents.folder";

    name = fields.Char({ string: "Name" });
    parent_folder_id = fields.Many2one({
        string: "Parent Workspace",
        relation: "documents.folder",
    });
    description = fields.Text({ string: "Description" });

    _records = [
        {
            id: 1,
            name: "Workspace1",
            description: "Workspace",
            parent_folder_id: false,
        },
    ];
}

export class DocumentsTag extends models.Model {
    _name = "documents.tag";
    get_tags() {
        return [];
    }
}

export class DocumentsWorkflowRule extends models.Model {
    _name = "documents.workflow.rule";
}

export class DocumentsShare extends models.Model {
    _name = "documents.share";
}

export class SpreadsheetTemplate extends models.Model {
    _name = "spreadsheet.template";

    name = fields.Char({ string: "Name", type: "char" });
    spreadsheet_data = fields.Binary({ string: "Spreadsheet Data" });
    thumbnail = fields.Binary({ string: "Thumbnail", type: "binary" });

    _records = [
        { id: 1, name: "Template 1", spreadsheet_data: "" },
        { id: 2, name: "Template 2", spreadsheet_data: "" },
    ];
}

export class SpreadsheetMixin extends models.Model {
    _name = "spreadsheet.mixin";

    spreadsheet_binary_data = fields.Binary({ string: "Spreadsheet file" });
    spreadsheet_data = fields.Text();
    thumbnail = fields.Binary();

    get_display_names_for_spreadsheet(args) {
        const result = [];
        for (const { model, id } of args) {
            const record = this.env[model].search_read([["id", "=", id]])[0];
            result.push(record?.display_name ?? null);
        }
        return result;
    }
}

export class ResCurrency extends models.Model {
    _name = "res.currency";

    name = fields.Char({ string: "Code" });
    symbol = fields.Char({ string: "Symbol" });
    position = fields.Selection({
        string: "Position",
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });
    decimal_places = fields.Integer({ string: "decimal" });

    get_company_currency_for_spreadsheet() {
        return {
            code: "EUR",
            symbol: "€",
            position: "after",
            decimalPlaces: 2,
        };
    }

    _records = [
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
    ];
}

export class Partner extends models.Model {
    _name = "partner";

    foo = fields.Integer({
        string: "Foo",
        store: true,
        searchable: true,
        aggregator: "sum",
        groupable: false,
    });
    bar = fields.Boolean({
        string: "Bar",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    name = fields.Char({
        string: "name",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    date = fields.Date({
        string: "Date",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    create_date = fields.Datetime({
        string: "Creation Date",
        store: true,
        sortable: true,
        groupable: true,
    });
    active = fields.Boolean({ string: "Active", default: true, searchable: true });
    product_id = fields.Many2one({
        string: "Product",
        relation: "product",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    tag_ids = fields.Many2many({
        string: "Tags",
        relation: "tag",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    probability = fields.Float({
        string: "Probability",
        searchable: true,
        store: true,
        aggregator: "avg",
    });
    field_with_array_agg = fields.Integer({
        string: "field_with_array_agg",
        searchable: true,
        aggregator: "array_agg",
    });
    currency_id = fields.Many2one({
        string: "Currency",
        relation: "res.currency",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    pognon = fields.Monetary({
        string: "Money!",
        currency_field: "currency_id",
        store: true,
        sortable: true,
        aggregator: "avg",
        groupable: true,
        searchable: true,
    });
    partner_properties = fields.Properties({
        string: "Properties",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
        definition_record: "product_id",
        definition_record_field: "properties_definitions",
    });
    jsonField = fields.Json({ string: "Json Field", store: true });
    user_ids = fields.Many2many({ relation: "res.users", string: "Users", searchable: true });

    _records = [
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
    ];
}

export class Product extends models.Model {
    _name = "product";

    name = fields.Char({ string: "Product Name" });
    display_name = fields.Char({ string: "Product Name" });
    active = fields.Boolean({ string: "Active", default: true });
    properties_definitions = fields.PropertiesDefinition();

    _records = [
        {
            id: 37,
            display_name: "xphone",
            name: "xphone",
        },
        {
            id: 41,
            display_name: "xpad",
            name: "xpad",
        },
    ];
}

export class Tag extends models.Model {
    _name = "tag";

    name = fields.Char({ string: "Tag Name" });

    _records = [
        {
            id: 42,
            name: "isCool",
        },
        {
            id: 67,
            name: "Growing",
        },
    ];
}

export function getBasicData() {
    return {
        "documents.document": { records: [] },
        "ir.model": { records: [] },
        "documents.folder": { records: [] },
        "documents.tag": {},
        "documents.workflow.rule": { records: [] },
        "documents.share": { records: [] },
        "spreadsheet.template": { records: [] },
        "res.currency": { records: [] },
        "res.users": { records: [] },
        partner: { records: [] },
        product: { records: [] },
        tag: { records: [] },
    };
}

export const SpreadsheetModels = {
    ...webModels,
    ...mailModels,
    DocumentsDocument,
    IrModel,
    IrUIMenu,
    IrActions,
    ResGroup,
    ResUsers,
    DocumentsFolder,
    DocumentsTag,
    DocumentsShare,
    DocumentsWorkflowRule,
    SpreadsheetTemplate,
    SpreadsheetMixin,
    ResCurrency,
    Partner,
    Product,
    Tag,
};

/**
 * Add the records inside serverData in the MockServer
 *
 * @param {ServerData} serverData
 */
export function addRecordsFromServerData(serverData) {
    for (const modelName of Object.keys(serverData.models)) {
        const records = serverData.models[modelName].records || [];
        if (!records.length) {
            continue;
        }
        const PyModel = Object.values(SpreadsheetModels).find((model) => model._name === modelName);
        if (!PyModel) {
            throw new Error(`Model ${modelName} not found inside SpreadsheetModels`);
        }
        checkRecordsValidity(modelName, records);
        PyModel._records = records;
    }
}

/**
 * Check if the records are valid.
 * This is mainly to avoid the mail's service crashing if the res.users are not correctly set.
 */
function checkRecordsValidity(modelName, records) {
    if (modelName === "res.users") {
        const serverUserId = serverState.userId;
        const currentUser = records.find((record) => record.id === serverUserId);
        if (!currentUser) {
            throw new Error(
                `The current user (${serverUserId}) is not in the records. did you forget to set serverState.userId ?`
            );
        }
        if (!currentUser.active) {
            throw new Error(`The current user (${serverUserId}) is not active`);
        }
        if (!currentUser.partner_id) {
            throw new Error(
                `The current user (${serverUserId}) has no partner_id. It should be set to serverState.partnerId`
            );
        }
    }
}

export function getPyEnv() {
    const mockServer = MockServer.current;
    if (!mockServer) {
        throw new Error("No mock server found");
    }
    return mockServer.env;
}
