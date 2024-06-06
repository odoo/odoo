/** @odoo-module */

import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { Model } = spreadsheet;

/**
 * @type {{
 *  NotLoaded: "NotLoaded",
 *  Loading: "Loading",
 *  Loaded: "Loaded",
 *  Error: "Error",
 * }}
 */
export const Status = {
    NotLoaded: "NotLoaded",
    Loading: "Loading",
    Loaded: "Loaded",
    Error: "Error",
};

/**
 * @typedef Dashboard
 * @property {number} id
 * @property {string} displayName
 * @property {string} status
 * @property {Model} [model]
 * @property {Error} [error]
 *
 * @typedef DashboardGroupData
 * @property {number} id
 * @property {string} name
 * @property {Array<number>} dashboardIds
 *
 * @typedef DashboardGroup
 * @property {number} id
 * @property {string} name
 * @property {Array<Dashboard>} dashboards
 *
 * @typedef {(dashboardId: number) => Promise<{ data: string, revisions: object[] }>} FetchDashboardData
 *
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {import("@web/core/orm_service").ORM} ORM
 */

export class DashboardLoader {
    /**
     * @param {OdooEnv} env
     * @param {ORM} orm
     * @param {FetchDashboardData} fetchDashboardData
     */
    constructor(env, orm, fetchDashboardData) {
        /** @private */
        this.env = env;
        /** @private */
        this.orm = orm;
        /** @private @type {Array<DashboardGroupData>} */
        this.groups = [];
        /** @private @type {Object<number, Dashboard>} */
        this.dashboards = {};
        /** @private */
        this.fetchDashboardData = fetchDashboardData;
    }

    /**
     * @param {Array<DashboardGroupData>} groups
     * @param {Object<number, Dashboard>} dashboards
     */
    restoreFromState(groups, dashboards) {
        this.groups = groups;
        this.dashboards = dashboards;
    }

    /**
     * Return data needed to restore a dashboard loader
     */
    getState() {
        return {
            groups: this.groups,
            dashboards: this.dashboards,
        };
    }

    async load() {
        const groups = await this._fetchGroups();
        this.groups = groups
            .filter((group) => group.dashboard_ids.length)
            .map((group) => ({
                id: group.id,
                name: group.name,
                dashboardIds: group.dashboard_ids,
            }));
        const dashboards = await this._fetchDashboardNames(this.groups);
        for (const dashboard of dashboards) {
            this.dashboards[dashboard.id] = {
                id: dashboard.id,
                displayName: dashboard.name,
                status: Status.NotLoaded,
            };
        }
    }

    /**
     * @param {number} dashboardId
     * @returns {Dashboard}
     */
    getDashboard(dashboardId) {
        const dashboard = this._getDashboard(dashboardId);
        if (dashboard.status === Status.NotLoaded) {
            dashboard.promise = this._loadDashboardData(dashboardId);
        }
        return dashboard;
    }

    /**
     * @returns {Array<DashboardGroup>}
     */
    getDashboardGroups() {
        return this.groups.map((section) => ({
            id: section.id,
            name: section.name,
            dashboards: section.dashboardIds.map((dashboardId) => ({
                id: dashboardId,
                displayName: this._getDashboard(dashboardId).displayName,
                status: this._getDashboard(dashboardId).status,
            })),
        }));
    }

    /**
     * @private
     * @returns {Promise<{id: number, name: string, dashboard_ids: number[]}[]>}
     */
    _fetchGroups() {
        return this.orm.searchRead(
            "spreadsheet.dashboard.group",
            [["dashboard_ids", "!=", false]],
            ["id", "name", "dashboard_ids"]
        );
    }

    /**
     * @private
     * @param {Array<DashboardGroupData>} groups
     * @returns {Promise}
     */
    _fetchDashboardNames(groups) {
        return this.orm.read(
            "spreadsheet.dashboard",
            groups.map((group) => group.dashboardIds).flat(),
            ["name"]
        );
    }

    /**
     * @private
     * @param {number} id
     * @returns {Dashboard}
     */
    _getDashboard(id) {
        if (!this.dashboards[id]) {
            this.dashboards[id] = { status: Status.NotLoaded, id, displayName: "" };
        }
        return this.dashboards[id];
    }

    /**
     * @private
     * @param {number} dashboardId
     */
    async _loadDashboardData(dashboardId) {
        const dashboard = this._getDashboard(dashboardId);
        dashboard.status = Status.Loading;
        try {
            const { data, revisions } = await this.fetchDashboardData(dashboardId);
            dashboard.model = this._createSpreadsheetModel(data, revisions);
            dashboard.status = Status.Loaded;
        } catch (error) {
            dashboard.error = error;
            dashboard.status = Status.Error;
            throw error;
        }
    }

    /**
     * Activate the first sheet of a model
     *
     * @param {Model} model
     */
    _activateFirstSheet(model) {
        const sheetId = model.getters.getActiveSheetId();
        const firstSheetId = model.getters.getSheetIds()[0];
        if (firstSheetId !== sheetId) {
            model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom: sheetId,
                sheetIdTo: firstSheetId,
            });
        }
    }

    /**
     * @private
     * @param {string} data
     * @param {object[]} revisions
     * @returns {Model}
     */
    _createSpreadsheetModel(data, revisions = []) {
        const dataSources = new DataSources(this.orm);
        const model = new Model(
            migrate(JSON.parse(data)),
            {
                evalContext: { env: this.env, orm: this.orm },
                mode: "dashboard",
                dataSources,
            },
            revisions
        );
        this._activateFirstSheet(model);
        dataSources.addEventListener("data-source-updated", () => model.dispatch("EVALUATE_CELLS"));
        return model;
    }
}
