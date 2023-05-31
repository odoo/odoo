/** @odoo-module */

import spreadsheet from "./o_spreadsheet_extended";
const { load, CorePlugin, tokenize, parse, convertAstNodes, astToFormula } = spreadsheet;
const { corePluginRegistry } = spreadsheet.registries;
const { markdownLink, parseMarkdownLink } = spreadsheet.helpers;
import {
    isMarkdownViewLink,
    parseViewLink,
    buildViewLink,
} from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell";
export const ODOO_VERSION = 6;

const MAP = {
    PIVOT: "ODOO.PIVOT",
    "PIVOT.HEADER": "ODOO.PIVOT.HEADER",
    "PIVOT.POSITION": "ODOO.PIVOT.POSITION",
    "FILTER.VALUE": "ODOO.FILTER.VALUE",
    LIST: "ODOO.LIST",
    "LIST.HEADER": "ODOO.LIST.HEADER",
};

const dmyRegex = /^([0|1|2|3][1-9])\/(0[1-9]|1[0-2])\/(\d{4})$/i;

export function migrate(data) {
    let _data = load(data, !!odoo.debug);
    const version = _data.odooVersion || 0;
    if (version < 1) {
        _data = migrate0to1(_data);
    }
    if (version < 2) {
        _data = migrate1to2(_data);
    }
    if (version < 3) {
        _data = migrate2to3(_data);
    }
    if (version < 4) {
        _data = migrate3to4(_data);
    }
    if (version < 5) {
        _data = migrate4to5(_data);
    }
    if (version < 6) {
        _data = migrate5to6(_data);
    }
    return _data;
}

function tokensToString(tokens) {
    return tokens.reduce((acc, token) => acc + token.value, "");
}

function migrate0to1(data) {
    for (const sheet of data.sheets) {
        for (const xc in sheet.cells || []) {
            const cell = sheet.cells[xc];
            if (cell.content && cell.content.startsWith("=")) {
                const tokens = tokenize(cell.content);
                for (const token of tokens) {
                    if (token.type === "SYMBOL" && token.value.toUpperCase() in MAP) {
                        token.value = MAP[token.value.toUpperCase()];
                    }
                }
                cell.content = tokensToString(tokens);
            }
        }
    }
    return data;
}

function migrate1to2(data) {
    for (const sheet of data.sheets) {
        for (const xc in sheet.cells || []) {
            const cell = sheet.cells[xc];
            if (cell.content && cell.content.startsWith("=")) {
                try {
                    cell.content = migratePivotDaysParameters(cell.content);
                } catch {
                    continue;
                }
            }
        }
    }
    return data;
}

/**
 * Migration of global filters
 */
function migrate2to3(data) {
    if (data.globalFilters) {
        for (const gf of data.globalFilters) {
            if (gf.fields) {
                gf.pivotFields = gf.fields;
                delete gf.fields;
            }
            if (
                gf.type === "date" &&
                typeof gf.defaultValue === "object" &&
                "year" in gf.defaultValue
            ) {
                switch (gf.defaultValue.year) {
                    case "last_year":
                        gf.defaultValue.yearOffset = -1;
                        break;
                    case "antepenultimate_year":
                        gf.defaultValue.yearOffset = -2;
                        break;
                    case "this_year":
                    case undefined:
                        gf.defaultValue.yearOffset = 0;
                        break;
                }
                delete gf.defaultValue.year;
            }
            if (!gf.listFields) {
                gf.listFields = {};
            }
            if (!gf.graphFields) {
                gf.graphFields = {};
            }
        }
    }
    return data;
}

/**
 * Migration of list/pivot names
 */
function migrate3to4(data) {
    if (data.lists) {
        for (const list of Object.values(data.lists)) {
            list.name = list.name || list.model;
        }
    }
    if (data.pivots) {
        for (const pivot of Object.values(data.pivots)) {
            pivot.name = pivot.name || pivot.model;
        }
    }
    return data;
}

function migrate4to5(data) {
    for (const filter of data.globalFilters || []) {
        for (const [id, fm] of Object.entries(filter.pivotFields || {})) {
            if (!(data.pivots && id in data.pivots)) {
                delete filter.pivotFields[id];
                continue;
            }
            if (!data.pivots[id].fieldMatching) {
                data.pivots[id].fieldMatching = {};
            }
            data.pivots[id].fieldMatching[filter.id] = { chain: fm.field, type: fm.type };
            if ("offset" in fm) {
                data.pivots[id].fieldMatching[filter.id].offset = fm.offset;
            }
        }
        delete filter.pivotFields;

        for (const [id, fm] of Object.entries(filter.listFields || {})) {
            if (!(data.lists && id in data.lists)) {
                delete filter.listFields[id];
                continue;
            }
            if (!data.lists[id].fieldMatching) {
                data.lists[id].fieldMatching = {};
            }
            data.lists[id].fieldMatching[filter.id] = { chain: fm.field, type: fm.type };
            if ("offset" in fm) {
                data.lists[id].fieldMatching[filter.id].offset = fm.offset;
            }
        }
        delete filter.listFields;

        const findFigureFromId = (id) => {
            for (const sheet of data.sheets) {
                const fig = sheet.figures.find((f) => f.id === id);
                if (fig) {
                    return fig;
                }
            }
            return undefined;
        };
        for (const [id, fm] of Object.entries(filter.graphFields || {})) {
            const figure = findFigureFromId(id);
            if (!figure) {
                delete filter.graphFields[id];
                continue;
            }
            if (!figure.data.fieldMatching) {
                figure.data.fieldMatching = {};
            }
            figure.data.fieldMatching[filter.id] = { chain: fm.field, type: fm.type };
            if ("offset" in fm) {
                figure.data.fieldMatching[filter.id].offset = fm.offset;
            }
        }
        delete filter.graphFields;
    }
    return data;
}

function migrate5to6(data) {
    if (data.pivots) {
        for (const pivot of Object.values(data.pivots)) {
            const measures = pivot.measures || [];
            pivot.measures = measures.map((m) => m.field || m);
        }
    }
    if (data.globalFilters) {
        for (const filter of data.globalFilters) {
            filter.model = filter.modelName;
            delete filter.modelName;
        }
    }
    for (const sheet of data.sheets) {
        for (const figure of sheet.figures || []) {
            if (figure.tag !== "chart" || !figure.data.type.startsWith("odoo_")) {
                continue;
            }
            const metaData = figure.data.metaData || {};
            const searchParams = figure.data.searchParams || {};
            figure.data.dataSourceDefinition = {
                id: figure.id,
                groupBy: metaData.groupBy,
                measure: metaData.measure,
                orderBy: metaData.order
                    ? { field: metaData.measure, asc: metaData.order.toLowerCase() === "asc" }
                    : undefined,
                model: metaData.resModel,
                domain: searchParams.domain,
                stacked: metaData.stacked,
            };
            delete figure.data.metaData;
            delete figure.data.searchParams;
        }
        for (const xc in sheet.cells || {}) {
            const cell = sheet.cells[xc];
            cell.content = renameViewLinkModelKey(cell.content);
        }
    }
    return data;
}

/**
 * Convert pivot formulas days parameters from day/month/year
 * format to the standard spreadsheet month/day/year format.
 * e.g. =PIVOT.HEADER(1,"create_date:day","30/07/2022") becomes =PIVOT.HEADER(1,"create_date:day","07/30/2022")
 * @param {string} formulaString
 * @returns {string}
 */
function migratePivotDaysParameters(formulaString) {
    const ast = parse(formulaString);
    const convertedAst = convertAstNodes(ast, "FUNCALL", (ast) => {
        if (["ODOO.PIVOT", "ODOO.PIVOT.HEADER"].includes(ast.value.toUpperCase())) {
            for (const subAst of ast.args) {
                if (subAst.type === "STRING") {
                    const date = subAst.value.match(dmyRegex);
                    if (date) {
                        subAst.value = `${[date[2], date[1], date[3]].join("/")}`;
                    }
                }
            }
        }
        return ast;
    });
    return "=" + astToFormula(convertedAst);
}

export function upgradeRevisions(revisions) {
    for (const revision of revisions) {
        if (revision.type === "REMOTE_REVISION") {
            revision.commands = revision.commands.map(upgradeCommand);
        }
    }
    return revisions;
}

function upgradeCommand(cmd) {
    switch (cmd.type) {
        case "INSERT_PIVOT": {
            if (!("metaData" in cmd.definition) || !("searchParams" in cmd.definition)) {
                return cmd;
            }
            const {
                colGroupBys,
                rowGroupBys,
                activeMeasures,
                resModel,
                sortedColumn,
            } = cmd.definition.metaData;
            const { domain, context } = cmd.definition.searchParams;
            const id = cmd.id;
            delete cmd.id;
            return {
                ...cmd,
                definition: {
                    id,
                    colGroupBys,
                    rowGroupBys,
                    model: resModel,
                    measures: activeMeasures,
                    domain,
                    context,
                    name: cmd.definition.name,
                    orderBy: sortedColumn
                        ? {
                              field: sortedColumn.measure,
                              asc: sortedColumn.order.toLowerCase() === "asc",
                              groupId: sortedColumn.groupId,
                          }
                        : undefined,
                },
            };
        }
        case "INSERT_ODOO_LIST": {
            if (!("metaData" in cmd.definition) || !("searchParams" in cmd.definition)) {
                return cmd;
            }
            const { columns, resModel } = cmd.definition.metaData;
            const { domain, context, orderBy } = cmd.definition.searchParams;
            const id = cmd.id;
            delete cmd.columns;
            delete cmd.id;
            return {
                ...cmd,
                definition: {
                    id,
                    model: resModel,
                    domain,
                    context,
                    columns,
                    orderBy: orderBy.map((order) => ({ field: order.name, asc: order.asc })),
                    name: cmd.definition.name,
                },
            };
        }
        case "CREATE_CHART": {
            if (!("metaData" in cmd.definition) || !("searchParams" in cmd.definition)) {
                return cmd;
            }
            const { resModel, measure, order, groupBy } = cmd.definition.metaData;
            const { domain, context } = cmd.definition.searchParams;
            delete cmd.definition.metaData;
            delete cmd.definition.searchParams;
            return {
                ...cmd,
                definition: {
                    ...cmd.definition,
                    dataSourceDefinition: {
                        id: cmd.definition.id,
                        model: resModel,
                        domain,
                        context,
                        measure,
                        groupBy,
                        orderBy: order
                            ? { field: measure, asc: order.toLowerCase() === "asc" }
                            : undefined,
                    },
                },
            };
        }
        case "ADD_GLOBAL_FILTER":
        case "EDIT_GLOBAL_FILTER": {
            if (!cmd.filter.modelName) {
                return cmd;
            }
            const modelName = cmd.filter.modelName;
            delete cmd.filter.modelName;
            return {
                ...cmd,
                filter: {
                    ...cmd.filter,
                    model: modelName,
                },
            };
        }
        case "UPDATE_CELL": {
            cmd.content = renameViewLinkModelKey(cmd.content);
            return cmd;
        }
        default:
            return cmd;
    }
}

/**
 * rename "modelName" key to "model" in view links
 * @param {string | undefined} content
 * @returns {string | undefined}
 */
function renameViewLinkModelKey(content) {
    if (content && isMarkdownViewLink(content)) {
        const { label, url } = parseMarkdownLink(content);
        const link = parseViewLink(url);
        if (!link.action.modelName) {
            return content;
        }
        link.action.model = link.action.modelName;
        delete link.action.modelName;
        return markdownLink(label, buildViewLink(link));
    }
    return content;
}

export default class OdooVersion extends CorePlugin {
    export(data) {
        data.odooVersion = ODOO_VERSION;
    }
}

OdooVersion.getters = [];

corePluginRegistry.add("odooMigration", OdooVersion);
