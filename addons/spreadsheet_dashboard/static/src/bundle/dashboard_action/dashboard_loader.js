/** @odoo-module */

import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { Model } from "@odoo/o-spreadsheet";

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
 * @property {Array<{id: number, name: string}>} dashboards
 *
 * @typedef DashboardGroup
 * @property {number} id
 * @property {string} name
 * @property {Array<Dashboard>} dashboards
 *
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {import("@web/core/orm_service").ORM} ORM
 */

export class DashboardLoader {
    /**
     * @param {OdooEnv} env
     * @param {ORM} orm
     */
    constructor(env, orm) {
        /** @private */
        this.env = env;
        /** @private */
        this.orm = orm;
        /** @private @type {Array<DashboardGroupData>} */
        this.groups = [];
        /** @private @type {Object<number, Dashboard>} */
        this.dashboards = {};
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
                dashboards: group.dashboard_ids,
            }));
        const dashboards = this.groups.map((group) => group.dashboards).flat();
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
            this._loadDashboardData(dashboardId);
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
            dashboards: section.dashboards.map((dashboard) => ({
                id: dashboard.id,
                displayName: dashboard.name,
                status: this._getDashboard(dashboard.id).status,
            })),
        }));
    }

    /**
     * @private
     * @returns {Promise<{id: number, name: string, dashboard_ids: number[]}[]>}
     */
    async _fetchGroups() {
        const groups = await this.orm.webSearchRead(
            "spreadsheet.dashboard.group",
            [["dashboard_ids", "!=", false]],
            {
                specification: {
                    name: {},
                    dashboard_ids: { fields: { name: {} } },
                },
            }
        );
        return groups.records;
    }

    /**
     * @private
     * @param {number} id
     * @returns {Dashboard|undefined}
     */
    _getDashboard(id) {
        if (!this.dashboards[id]) {
            throw new Error(`Dashboard ${id} does not exist`);
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
            const { snapshot, revisions } = await this.orm.call(
                "spreadsheet.dashboard",
                "get_readonly_dashboard",
                [dashboardId]
            );
            dashboard.model = this._createSpreadsheetModel(snapshot, revisions);
            dashboard.status = Status.Loaded;
        } catch (error) {
            dashboard.error = error;
            dashboard.status = Status.Error;
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
     * @param {object} snapshot
     * @param {object[]} revisions
     * @returns {Model}
     */
    _createSpreadsheetModel(snapshot, revisions = []) {
        const dataSources = new DataSources(this.env);
        const model = new Model(
            migrate(snapshot),
            {
                custom: { env: this.env, orm: this.orm, dataSources },
                mode: "dashboard",
            },
            revisions
        );
        this._activateFirstSheet(model);
        dataSources.addEventListener("data-source-updated", () => model.dispatch("EVALUATE_CELLS"));
        return model;
    }
}
