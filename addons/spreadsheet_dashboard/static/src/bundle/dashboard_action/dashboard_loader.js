import { Model } from "@odoo/o-spreadsheet";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { createDefaultCurrency } from "@spreadsheet/currency/helpers";
import { _t } from "@web/core/l10n/translation";

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
    constructor(env, orm, geoJsonService) {
        /** @private */
        this.env = env;
        /** @private */
        this.orm = orm;
        /** @private @type {Array<DashboardGroupData>} */
        this.groups = [];
        /** @private @type {Object<number, Dashboard>} */
        this.dashboards = {};
        this.geoJsonService = geoJsonService;
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
            .filter((group) => group.published_dashboard_ids.length)
            .map((group) => ({
                id: group.id,
                name: group.name,
                dashboards: group.published_dashboard_ids,
            }));
        const dashboards = this.groups.map((group) => group.dashboards).flat();
        for (const dashboard of dashboards) {
            this.dashboards[dashboard.id] = {
                id: dashboard.id,
                displayName: dashboard.name,
                status: Status.NotLoaded,
                isFavorite: dashboard.is_favorite,
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
        const favoriteDashboards = this._getFavoriteDashboards();
        const dashboardGroups = this.groups.map((section) => ({
            id: section.id,
            name: section.name,
            dashboards: section.dashboards.map((dashboard) => ({
                id: dashboard.id,
                displayName: dashboard.name,
                status: this._getDashboard(dashboard.id).status,
            })),
        }));

        return favoriteDashboards.length
            ? [
                  { id: "favorites", name: _t("FAVORITES"), dashboards: favoriteDashboards },
                  ...dashboardGroups,
              ]
            : dashboardGroups;
    }

    /**
     * @private
     * @returns {Promise<{id: number, name: string, published_dashboard_ids: number[]}[]>}
     */
    async _fetchGroups() {
        const groups = await this.orm.webSearchRead(
            "spreadsheet.dashboard.group",
            [["published_dashboard_ids", "!=", false]],
            {
                specification: {
                    name: {},
                    published_dashboard_ids: { fields: { name: {}, is_favorite: {} } },
                },
            }
        );
        return groups.records;
    }

    /**
     * Filters and returns an array of favorite dashboards.
     * @returns {Array<Dashboard>}
     */
    _getFavoriteDashboards() {
        const favoriteDashboards = [];
        this.groups
            .flatMap((group) => group.dashboards)
            .forEach((dashboard) => {
                const dashboardData = this._getDashboard(dashboard.id);
                if (dashboardData.isFavorite) {
                    favoriteDashboards.push({
                        id: dashboard.id,
                        displayName: dashboard.name,
                        status: dashboardData.status,
                    });
                }
            });

        return favoriteDashboards;
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
            const result = await this.env.services.http.get(
                `/spreadsheet/dashboard/data/${dashboardId}`
            );
            const { snapshot, revisions, default_currency, is_sample } = result;
            dashboard.model = this._createSpreadsheetModel(snapshot, revisions, default_currency);
            dashboard.status = Status.Loaded;
            dashboard.isSample = is_sample;
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
     * @param {object} snapshot
     * @param {object[]} revisions
     * @param {object} [defaultCurrency]
     * @returns {Model}
     */
    _createSpreadsheetModel(snapshot, revisions = [], currency) {
        const odooDataProvider = new OdooDataProvider(this.env);
        const model = new Model(
            snapshot,
            {
                custom: { env: this.env, orm: this.orm, odooDataProvider },
                mode: "dashboard",
                defaultCurrency: createDefaultCurrency(currency),
                external: { geoJsonService: this.geoJsonService },
            },
            revisions
        );
        this._activateFirstSheet(model);
        odooDataProvider.addEventListener("data-source-updated", () =>
            model.dispatch("EVALUATE_CELLS")
        );
        return model;
    }
}
