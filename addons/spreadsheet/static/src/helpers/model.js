/** @odoo-module **/
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { Model } = spreadsheet;

/**
 * @param {object} params
 * @param {object} params.orm
 * @param {object} [params.data]
 * @param {object[]} [params.revisions]
 * @param {object} [params.env]
 * @param {object} [params.config]
 *
 * @returns
 */
export function createSpreadsheetModel({ orm, data, revisions, env, config }) {
    const dataSources = new DataSources(orm);
    const model = new Model(
        migrate(data || {}),
        { ...config, custom: { dataSources, env } },
        revisions || []
    );
    dataSources.addEventListener("data-source-updated", () => model.dispatch("EVALUATE_CELLS"));
    return model;
}
