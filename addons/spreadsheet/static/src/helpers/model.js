/** @odoo-module */
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { Model, parse, helpers, iterateAstNodes } from "@odoo/o-spreadsheet";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";

const { toCartesian, UuidGenerator, createEmptySheet } = helpers;
const uuidGenerator = new UuidGenerator();

export async function fetchSpreadsheetModel(env, resModel, resId) {
    const { data, revisions } = await env.services.orm.call(resModel, "join_spreadsheet_session", [
        resId,
    ]);
    return createSpreadsheetModel({ env, data, revisions });
}

export function createSpreadsheetModel({ env, data, revisions }) {
    const dataSources = new DataSources(env);
    const model = new Model(migrate(data), { custom: { dataSources } }, revisions);
    return model;
}

/**
 * Ensure that the spreadsheet does not contains cells that are in loading state
 * @param {Model} model
 * @returns {Promise<void>}
 */
export async function waitForDataLoaded(model) {
    const dataSources = model.config.custom.dataSources;
    await dataSources.waitForAllLoaded();
    return new Promise((resolve, reject) => {
        function check() {
            model.dispatch("EVALUATE_CELLS");
            if (isLoaded(model)) {
                dataSources.removeEventListener("data-source-updated", check);
                resolve();
            }
        }
        dataSources.addEventListener("data-source-updated", check);
        check();
    });
}

/**
 * @param {Model} model
 * @returns {object}
 */
export async function freezeOdooData(model) {
    await waitForDataLoaded(model);
    const data = model.exportData();
    for (const sheet of Object.values(data.sheets)) {
        for (const [xc, cell] of Object.entries(sheet.cells)) {
            if (containsOdooFunction(cell.content)) {
                const { col, row } = toCartesian(xc);
                const sheetId = sheet.id;
                const evaluatedCell = model.getters.getEvaluatedCell({
                    sheetId,
                    col,
                    row,
                });
                cell.content = evaluatedCell.formattedValue;
                if (evaluatedCell.format) {
                    cell.format = getItemId(evaluatedCell.format, data.formats);
                }
            }
        }
        for (const figure of sheet.figures) {
            if (figure.tag === "chart" && figure.data.type.startsWith("odoo_")) {
                await loadBundle("web.chartjs_lib");
                const img = odooChartToImage(model, figure);
                figure.tag = "image";
                figure.data = {
                    path: img,
                    size: { width: figure.width, height: figure.height },
                };
            }
        }
    }
    if (model.getters.getGlobalFilters().length === 0) {
        return data;
    }
    data.sheets.push(exportGlobalFiltersToSheet(model, data));
    return data;
}

function exportGlobalFiltersToSheet(model, data) {
    const styles = Object.entries(data.styles);
    data.styles[styles.length + 1] = { bold: true };

    const cells = {};
    cells["A1"] = { content: _t("Filter"), style: styles.length + 1 };
    cells["B1"] = { content: _t("Value"), style: styles.length + 1 };
    let row = 2;
    for (const filter of data.globalFilters) {
        const content = model.getters.getFilterDisplayValue(filter.label);
        cells[`A${row}`] = { content: filter.label };
        cells[`B${row}`] = { content };
        filter["value"] = content;
        row++;
    }
    return {
        ...createEmptySheet(uuidGenerator.uuidv4(), _t("Active Filters")),
        cells,
        colNumber: 2,
        rowNumber: model.getters.getGlobalFilters().length + 1,
    };
}

/**
 * copy-pasted from o-spreadsheet. Should be exported
 * Get the id of the given item (its key in the given dictionnary).
 * If the given item does not exist in the dictionary, it creates one with a new id.
 */
export function getItemId(item, itemsDic) {
    for (const [key, value] of Object.entries(itemsDic)) {
        if (value === item) {
            return parseInt(key, 10);
        }
    }

    // Generate new Id if the item didn't exist in the dictionary
    const ids = Object.keys(itemsDic);
    const maxId = ids.length === 0 ? 0 : Math.max(...ids.map((id) => parseInt(id, 10)));

    itemsDic[maxId + 1] = item;
    return maxId + 1;
}

/**
 *
 * @param {string | undefined} content
 * @returns {boolean}
 */
function containsOdooFunction(content) {
    if (
        !content ||
        !content.startsWith("=") ||
        (!content.toUpperCase().includes("ODOO.") && !content.toUpperCase().includes("_T"))
    ) {
        return false;
    }
    try {
        const ast = parse(content);
        return iterateAstNodes(ast).some(
            (ast) =>
                ast.type === "FUNCALL" &&
                (ast.value.toUpperCase().startsWith("ODOO.") ||
                    ast.value.toUpperCase().startsWith("_T"))
        );
    } catch {
        return false;
    }
}

function isLoaded(model) {
    for (const sheetId of model.getters.getSheetIds()) {
        for (const cell of Object.values(model.getters.getEvaluatedCells(sheetId))) {
            if (cell.type === "error" && cell.error.message === _t("Data is loading")) {
                return false;
            }
        }
    }
    return true;
}

/**
 * Return the chart figure as a base64 image.
 * "data:image/png;base64,iVBORw0KGg..."
 * @param {Model} model
 * @param {object} figure
 * @returns {string}
 */
function odooChartToImage(model, figure) {
    const runtime = model.getters.getChartRuntime(figure.id);
    // wrap the canvas in a div with a fixed size because chart.js would
    // fill the whole page otherwise
    const div = document.createElement("div");
    div.style.width = `${figure.width}px`;
    div.style.height = `${figure.height}px`;
    const canvas = document.createElement("canvas");
    div.append(canvas);
    canvas.setAttribute("width", figure.width);
    canvas.setAttribute("height", figure.height);
    // we have to add the canvas to the DOM otherwise it won't be rendered
    document.body.append(div);
    runtime.chartJsConfig.plugins = [backgroundColorPlugin];
    const chart = new Chart(canvas, runtime.chartJsConfig);
    const img = chart.toBase64Image();
    chart.destroy();
    div.remove();
    return img;
}

/**
 * Custom chart.js plugin to set the background color of the canvas
 * https://github.com/chartjs/Chart.js/blob/8fdf76f8f02d31684d34704341a5d9217e977491/docs/configuration/canvas-background.md
 */
const backgroundColorPlugin = {
    id: "customCanvasBackgroundColor",
    beforeDraw: (chart, args, options) => {
        const { ctx } = chart;
        ctx.save();
        ctx.globalCompositeOperation = "destination-over";
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
    },
};
