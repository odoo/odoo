import {
    MockServer,
    defineActions,
    defineModels,
    fields,
    models,
    onRpc,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { RPCError } from "@web/core/network/rpc";

/**
 * @typedef {object} ServerData
 * @property {object} [models]
 * @property {object} [views]
 * @property {object} [menus]
 * @property {object} [actions]
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
        <list string="Partners">
            <field name="foo"/>
            <field name="bar"/>
            <field name="date"/>
            <field name="product_id"/>
        </list>
    `;
}

export function getBasicGraphArch() {
    return /* xml */ `
        <graph string="PartnerGraph">
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
        views: {},
    };
}

/**
 *
 * @param {string} model
 * @param {Array<string>} columns
 * @param {{name: string, asc: boolean}[]} orderBy
 *
 * @returns { {definition: Object, columns: Array<Object>}}
 */
export function generateListDefinition(model, columns, actionXmlId, orderBy = []) {
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
                orderBy,
            },
            name: "List",
            actionXmlId,
        },
        columns: cols,
    };
}

export function getBasicListArchs() {
    return {
        "partner,false,list": getBasicListArch(),
    };
}

function mockSpreadsheetDataController(_request, { res_model, res_id }) {
    const [record] = this.env[res_model].search_read([["id", "=", parseInt(res_id)]]);
    if (!record) {
        const error = new RPCError(`Spreadsheet ${res_id} does not exist`);
        error.data = {};
        throw error;
    }
    return {
        data: JSON.parse(record.spreadsheet_data),
        name: record.name,
        revisions: [],
        isReadonly: false,
        writable_rec_name_field: "name",
    };
}

onRpc("/spreadsheet/data/<string:res_model>/<int:res_id>", mockSpreadsheetDataController);

export function defineSpreadsheetModels() {
    defineModels(SpreadsheetModels);
}

export function defineSpreadsheetActions() {
    defineActions([
        {
            id: 1,
            name: "partner Action",
            res_model: "partner",
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

export class IrModel extends webModels.IrModel {
    display_name_for(models) {
        const records = this.env["ir.model"].search_read([["model", "in", models]]);
        return records.map((record) => ({
            model: record.model,
            display_name: record.name,
        }));
    }

    /**
     * @param {string[]} modelNames
     */
    has_searchable_parent_relation(modelNames) {
        return Object.fromEntries(modelNames.map((modelName) => [modelName, false]));
    }

    get_available_models() {
        return this.env["ir.model"].search_read([], ["display_name", "model"]);
    }

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
        {
            id: 56,
            name: "Currency",
            model: "res.currency",
        },
        {
            id: 57,
            name: "Tag",
            model: "tag",
        },
    ];
}

export class IrUIMenu extends models.Model {
    _name = "ir.ui.menu";

    name = fields.Char({ string: "Name" });
    action = fields.Char({ string: "Action" });
    group_ids = fields.Many2many({ string: "Groups", relation: "res.group" });
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
    group_ids = fields.Many2many({ string: "Groups", relation: "res.group" });
}

export class SpreadsheetMixin extends models.Model {
    _name = "spreadsheet.mixin";

    spreadsheet_binary_data = fields.Binary({ string: "Spreadsheet file" });
    spreadsheet_data = fields.Text();
    display_thumbnail = fields.Binary();

    get_display_names_for_spreadsheet(args) {
        const result = [];
        for (const { model, id } of args) {
            const record = this.env[model].search_read([["id", "=", id]])[0];
            result.push(record?.display_name ?? null);
        }
        return result;
    }

    get_selector_spreadsheet_models() {
        return [
            {
                model: "documents.document",
                display_name: "Spreadsheets",
                allow_create: true,
            },
        ];
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

export class ResCountry extends webModels.ResCountry {
    _name = "res.country";
    name = fields.Char({ string: "Country" });
    code = fields.Char({ string: "Code" });

    _records = [
        { id: 1, name: "Belgium", code: "BE" },
        { id: 2, name: "France", code: "FR" },
        { id: 3, name: "United States", code: "US" },
    ];
}

export class ResCountryState extends models.Model {
    _name = "res.country.state";
    name = fields.Char({ string: "Name" });
    code = fields.Char({ string: "Code" });
    country_id = fields.Many2one({ relation: "res.country" });
    display_name = fields.Char({ string: "Display Name" });

    _records = [
        { id: 1, name: "California", code: "CA", country_id: 3, display_name: "California (US)" },
        { id: 2, name: "New York", code: "NY", country_id: 3, display_name: "New York (US)" },
        { id: 3, name: "Texas", code: "TX", country_id: 3, display_name: "Texas (US)" },
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
    active = fields.Boolean({
        string: "Active",
        default: true,
        searchable: true,
        groupable: false,
    });
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
        groupable: false,
    });
    field_with_array_agg = fields.Integer({
        string: "field_with_array_agg",
        searchable: true,
        groupable: false,
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
    jsonField = fields.Json({ string: "Json Field", store: true, groupable: false });
    user_ids = fields.Many2many({
        relation: "res.users",
        string: "Users",
        searchable: true,
        groupable: false,
    });

    _records = [
        {
            id: 1,
            foo: 12,
            bar: true,
            name: "Raoul",
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
            name: "Steven",
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
            name: "Taylor",
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
            name: "Zara",
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

    // TODO: check which views are actually needed in the tests
    _views = {
        list: getBasicListArch(),
        pivot: getBasicPivotArch(),
        graph: getBasicGraphArch(),
    };
}

export class Product extends models.Model {
    _name = "product";

    name = fields.Char({ string: "Product Name" });
    display_name = fields.Char({ string: "Product Name" });
    active = fields.Boolean({ string: "Active", default: true });
    template_id = fields.Many2one({
        string: "Template",
        relation: "product",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    properties_definitions = fields.PropertiesDefinition();
    pognon = fields.Monetary({
        string: "Money!",
        currency_field: "currency_id",
        store: true,
        sortable: true,
        aggregator: "avg",
        groupable: true,
        searchable: true,
    });
    currency_id = fields.Many2one({
        string: "Currency",
        relation: "res.currency",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });

    _records = [
        {
            id: 37,
            display_name: "xphone",
            name: "xphone",
            currency_id: 2,
            pognon: 699.99,
        },
        {
            id: 41,
            display_name: "xpad",
            template_id: 37,
            name: "xpad",
            currency_id: 2,
            pognon: 599.99,
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
        "documents.document": {},
        "ir.model": {},
        "ir.embedded.actions": {},
        "documents.tag": {},
        "spreadsheet.template": {},
        "res.currency": {},
        "res.users": {},
        partner: {},
        product: {},
        tag: {},
    };
}

export const SpreadsheetModels = {
    ...webModels,
    ...mailModels,
    IrModel,
    IrUIMenu,
    IrActions,
    ResGroup,
    ResUsers,
    ResCountry,
    ResCountryState,
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
        const records = serverData.models[modelName].records;
        if (!records) {
            continue;
        }
        const PyModel = getSpreadsheetModel(modelName);
        if (!PyModel) {
            throw new Error(`Model ${modelName} not found inside SpreadsheetModels`);
        }
        checkRecordsValidity(modelName, records);
        PyModel._records = records;
    }
}

/**
 * Add the views inside serverData in the MockServer
 *
 * @param {ServerData} serverData
 *
 * @example
 * addViewsFromServerData({ "partner,false,search": "<search/>" });
 * Will set the default search view for the partner model
 */
export function addViewsFromServerData(serverData) {
    for (const fullViewKey of Object.keys(serverData.views)) {
        const viewArch = serverData.views[fullViewKey];
        const splitted = fullViewKey.split(",");
        const modelName = splitted[0];
        const viewType = splitted[2];
        const recordId = splitted[1];
        const PyModel = getSpreadsheetModel(modelName);
        if (!PyModel) {
            throw new Error(`Model ${modelName} not found inside SpreadsheetModels`);
        }
        const viewKey = viewType + "," + recordId;
        PyModel._views[viewKey] = viewArch;
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

export function getSpreadsheetModel(modelName) {
    return Object.values(SpreadsheetModels).find((model) => model._name === modelName);
}
