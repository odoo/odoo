/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooCorePlugin } from "@spreadsheet/plugins";
const { tokenize, parse, convertAstNodes, astToFormula } = spreadsheet;
const { corePluginRegistry, migrationStepRegistry } = spreadsheet.registries;

export const ODOO_VERSION = 12;

const MAP_V1 = {
    PIVOT: "ODOO.PIVOT",
    "PIVOT.HEADER": "ODOO.PIVOT.HEADER",
    "PIVOT.POSITION": "ODOO.PIVOT.POSITION",
    "FILTER.VALUE": "ODOO.FILTER.VALUE",
    LIST: "ODOO.LIST",
    "LIST.HEADER": "ODOO.LIST.HEADER",
};

const MAP_FN_NAMES_V10 = {
    "ODOO.PIVOT": "PIVOT.VALUE",
    "ODOO.PIVOT.HEADER": "PIVOT.HEADER",
    "ODOO.PIVOT.TABLE": "PIVOT",
};

const dmyRegex = /^([0|1|2|3][1-9])\/(0[1-9]|1[0-2])\/(\d{4})$/i;

migrationStepRegistry.add("odoo_migration", {
    versionFrom: "16.1",
    migrate(data) {
        return migrateOdooData(data);
    },
});

function migrateOdooData(data) {
    const version = data.odooVersion || 0;
    if (version < 1) {
        data = migrate0to1(data);
    }
    if (version < 2) {
        data = migrate1to2(data);
    }
    if (version < 3) {
        data = migrate2to3(data);
    }
    if (version < 4) {
        data = migrate3to4(data);
    }
    if (version < 5) {
        data = migrate4to5(data);
    }
    if (version < 6) {
        data = migrate5to6(data);
    }
    if (version < 7) {
        data = migrate6to7(data);
    }
    if (version < 8) {
        data = migrate7to8(data);
    }
    if (version < 9) {
        data = migrate8to9(data);
    }
    if (version < 10) {
        data = migrate9to10(data);
    }
    if (version < 11) {
        data = migrate10to11(data);
    }
    if (version < 12) {
        data = migrate11to12(data);
    }
    return data;
}

function parseDimension(dimension) {
    const [name, granularity] = dimension.split(":");
    if (granularity) {
        return { name, granularity };
    }
    return { name };
}

function renameFunctions(data, map) {
    for (const sheet of data.sheets || []) {
        for (const xc in sheet.cells || []) {
            const cell = sheet.cells[xc];
            if (cell.content && cell.content.startsWith("=")) {
                const tokens = tokenize(cell.content);
                for (const token of tokens) {
                    if (token.type === "SYMBOL" && token.value.toUpperCase() in map) {
                        token.value = map[token.value.toUpperCase()];
                    }
                }
                cell.content = tokensToString(tokens);
            }
        }
    }
    return data;
}

function tokensToString(tokens) {
    return tokens.reduce((acc, token) => acc + token.value, "");
}

function migrate0to1(data) {
    return renameFunctions(data, MAP_V1);
}

function migrate1to2(data) {
    for (const sheet of data.sheets || []) {
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

function migrate5to6(data) {
    if (!data.globalFilters?.length) {
        return data;
    }
    for (const filter of data.globalFilters) {
        if (filter.type === "date" && ["year", "quarter", "month"].includes(filter.rangeType)) {
            if (filter.defaultsToCurrentPeriod) {
                filter.defaultValue = `this_${filter.rangeType}`;
            }
            filter.rangeType = "fixedPeriod";
        }
        delete filter.defaultsToCurrentPeriod;
    }
    return data;
}

/**
 * Migrate the pivot data to add the type, by default "ODOO". And replace the
 * pivot with a new object that contains type and definition (the old pivot).
 */
function migrate6to7(data) {
    if (data.pivots) {
        for (const [id, definition] of Object.entries(data.pivots)) {
            definition.measures = definition.measures.map((measure) => measure.field);
            const fieldMatching = definition.fieldMatching;
            delete definition.fieldMatching;
            data.pivots[id] = {
                type: "ODOO",
                definition,
                fieldMatching,
            };
        }
    }
    return data;
}

function migrate7to8(data) {
    if (data.pivots) {
        for (const [id, pivot] of Object.entries(data.pivots)) {
            data.pivots[id] = {
                type: pivot.type,
                fieldMatching: pivot.fieldMatching,
                ...pivot.definition,
            };
        }
    }
    return data;
}

function migrate8to9(data) {
    if (data.pivots) {
        for (const id of Object.keys(data.pivots)) {
            data.pivots[id].formulaId = id;
        }
    }
    return data;
}

function migrate9to10(data) {
    return renameFunctions(data, MAP_FN_NAMES_V10);
}

function migrate10to11(data) {
    if (data.pivots) {
        for (const pivot of Object.values(data.pivots)) {
            pivot.measures = pivot.measures.map((measure) => ({
                name: measure,
            }));
            pivot.columns = pivot.colGroupBys.map(parseDimension);
            delete pivot.colGroupBys;
            pivot.rows = pivot.rowGroupBys.map(parseDimension);
            delete pivot.rowGroupBys;
        }
    }
    return data;
}

function migrate11to12(data) {
    // remove the calls to ODOO.PIVOT.POSITION and replace
    // the previous argument to a relative position
    for (const sheet of data.sheets || []) {
        for (const xc in sheet.cells || []) {
            const cell = sheet.cells[xc];
            if (
                cell.content &&
                cell.content.startsWith("=") &&
                cell.content.includes("ODOO.PIVOT.POSITION")
            ) {
                const tokens = tokenize(cell.content);
                /* given that odoo.pivot.position is automatically set, we know that:
                1) it is always on the form of ODOO.PIVOT.POSITION(1, ...)
                2) it is always preceded by a dimension of a pivot or header, inside another pivot formula
                3) there is only one odoo.pivot.position per cell
                4) odoo.pivot.position can only exist after the 3rd token and needs at least 7 tokens to be valid*/
                for (let i = 2; i < tokens.length - 7; i++) {
                    const token = tokens[i];
                    if (
                        token.type === "SYMBOL" &&
                        token.value.toUpperCase() === "ODOO.PIVOT.POSITION"
                    ) {
                        const order = tokens[i + 6];
                        tokens[i - 2].value = '"#' + tokens[i - 2].value.slice(1); // "dimension" becomes "#dimension"
                        tokens.splice(i, 7); // remove "ODOO.PIVOT.POSITION", "(", "1", ",", "dimension", ", ", order
                        // tokens[i-1] is the comma before odoo.pivot.position
                        tokens[i] = order;
                        cell.content = tokensToString(tokens);
                    }
                }
            }
        }
    }
    return data;
}

export class OdooVersion extends OdooCorePlugin {
    static getters = /** @type {const} */ ([]);

    export(data) {
        data.odooVersion = ODOO_VERSION;
    }
}

corePluginRegistry.add("odooMigration", OdooVersion);
