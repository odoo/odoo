import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    getDefaultValue,
    getFacetInfo,
    isEmptyFilterValue,
} from "@spreadsheet/global_filters/helpers";
import { user } from "@web/core/user";
import { deepEqual } from "@web/core/utils/objects";

export function getActiveFilterValuesById(filterNodes) {
    const filterValuesById = {};
    for (const { globalFilter, value } of filterNodes) {
        if (!isEmptyFilterValue(globalFilter, value)) {
            filterValuesById[globalFilter.id] = value;
        }
    }
    return filterValuesById;
}

export function buildFilterNodesFromValues(getters, filterValuesById) {
    return getters.getGlobalFilters().map((gf) => ({
        globalFilter: gf,
        value: filterValuesById[gf.id] ? { ...filterValuesById[gf.id] } : getDefaultValue(gf.type),
    }));
}

function normalizeValue(filter, value) {
    return isEmptyFilterValue(filter, value) ? undefined : value;
}

export class DashboardSearchModel {
    constructor(env, orm, spreadsheetModel) {
        this.env = env;
        this.orm = orm;
        this.spreadsheetModel = spreadsheetModel;
        this.state = proxy({
            isLoading: false,
            facets: [],
        });
        this.spreadsheetModel.on("command-dispatched", this, (command) => {
            if (command.type === "SET_MANY_GLOBAL_FILTER_VALUE") {
                this._refreshFacets();
            }
        });
    }

    async loadFavoritesForDashboard(dashboardId) {
        this.state.isLoading = true;
        this.favoriteRecordMap = {};
        this.firstDateFilter = undefined;
        this.activeDashboardId = dashboardId;

        let defaultFavoriteId = undefined;
        const favoriteRecords = await this.orm.searchRead(
            "spreadsheet.dashboard.favorite.filters",
            [
                ["dashboard_id", "=", dashboardId],
                ["user_ids", "in", [false, user.userId]],
            ],
            ["name", "is_default", "global_filters", "user_ids"]
        );

        for (const record of favoriteRecords) {
            const favoriteFilters = buildFilterNodesFromValues(
                this.spreadsheetModel.getters,
                record.global_filters
            );

            this.favoriteRecordMap[record.id] = {
                id: record.id,
                description: record.name,
                isDefault: record.is_default,
                userIds: record.user_ids,
                favoriteFilters,
            };

            if (record.is_default) {
                defaultFavoriteId = record.id;
            }
        }
        if (defaultFavoriteId) {
            this._applyFavoriteFilter(defaultFavoriteId);
        } else {
            await this._refreshFacets();
        }
        this.state.isLoading = false;
    }

    async _refreshFacets() {
        const facets = [];
        const getters = this.spreadsheetModel.getters;
        const allFilters = [...getters.getGlobalFilters()];

        const pushFavoriteFacet = (id, label) => {
            facets.push({
                id,
                type: "favorite",
                icon: "fa fa-star",
                values: [label],
            });
        };
        const pushFieldFacet = async (filter, value) => {
            const info = await getFacetInfo(this.env, filter, value, getters);
            facets.push({
                id: info.id,
                type: "field",
                title: info.title,
                values: info.values,
                operator: info.operator,
                separator: info.separator,
            });
        };

        // Remove first date filter (handled separately in UI)
        const dateIdx = allFilters.findIndex((f) => f.type === "date");
        if (dateIdx !== -1) {
            this.firstDateFilter = allFilters.splice(dateIdx, 1)[0];
        }

        if (this.activeFavoriteId) {
            const fav = this.favoriteRecordMap[this.activeFavoriteId];
            pushFavoriteFacet(fav.id, fav.description);

            const favoriteMap = this._getFavoriteMap(this.activeFavoriteId);
            for (const filter of allFilters) {
                const currentValue = normalizeValue(
                    filter,
                    getters.getGlobalFilterValue(filter.id)
                );
                const favoriteValue = normalizeValue(filter, favoriteMap.get(filter.id));

                if (deepEqual(currentValue, favoriteValue)) {
                    // Filter matches its favorite baseline — no override to show.
                    continue;
                }

                if (currentValue !== undefined) {
                    // Filter has an active value that differs from the baseline.
                    await pushFieldFacet(filter, currentValue);
                } else if (favoriteValue !== undefined) {
                    // Filter was part of the favorite baseline but has been explicitly cleared.
                    facets.push({
                        id: filter.id,
                        type: "field",
                        title: filter.label,
                        values: [_t("(Any value)")],
                        operator: _t("has"),
                        separator: "",
                    });
                }
            }
        } else {
            for (const filter of allFilters) {
                if (!getters.isGlobalFilterActive(filter.id)) {
                    continue;
                }
                await pushFieldFacet(filter, getters.getGlobalFilterValue(filter.id));
            }
        }
        this.state.facets = facets;
    }

    async createFavoriteRecord(name, isDefault, filterNodes) {
        const payload = {
            name,
            dashboard_id: this.activeDashboardId,
            global_filters: getActiveFilterValuesById(filterNodes),
            is_default: isDefault,
            user_ids: [user.userId],
        };
        const [serverSideId] = await this.orm.create("spreadsheet.dashboard.favorite.filters", [
            payload,
        ]);
        this.favoriteRecordMap[serverSideId] = {
            id: serverSideId,
            description: name,
            isDefault,
            userIds: [user.userId],
            favoriteFilters: filterNodes,
        };
        this._applyFavoriteFilter(serverSideId);
        return serverSideId;
    }

    clearFilter(filterId) {
        if (this.activeFavoriteId === filterId) {
            this._clearFavoriteFilters(filterId);
            return;
        }
        if (this.activeFavoriteId) {
            // The user is removing a field override while a favorite is active.
            const fav = this.favoriteRecordMap[this.activeFavoriteId];
            const favoriteNode = fav.favoriteFilters.find((f) => f.globalFilter.id === filterId);
            if (favoriteNode) {
                const baselineValue = normalizeValue(favoriteNode.globalFilter, favoriteNode.value);
                this.spreadsheetModel.dispatch("SET_GLOBAL_FILTER_VALUE", {
                    id: filterId,
                    value: baselineValue,
                });
                this._refreshFacets();
                return;
            }
        }

        // No active favorite, or filter not tracked by the favorite — clear it outright.
        this.spreadsheetModel.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filterId });
        this._refreshFacets();
    }

    getFavoriteList(filterFn) {
        return Object.values(this.favoriteRecordMap)
            .map((fav) => ({
                ...fav,
                isActive: fav.id === this.activeFavoriteId,
            }))
            .filter((f) => !filterFn || filterFn(f));
    }

    _getFavoriteMap(favoriteId) {
        const fav = this.favoriteRecordMap[favoriteId];
        return new Map(fav.favoriteFilters.map((f) => [f.globalFilter.id, f.value]));
    }

    toggleFavorite(localId) {
        if (this.activeFavoriteId === localId) {
            this._clearFavoriteFilters(localId);
        } else {
            this._applyFavoriteFilter(localId);
        }
    }

    _applyFavoriteFilter(favoriteId) {
        this.activeFavoriteId = favoriteId;

        const filters = [];
        const getters = this.spreadsheetModel.getters;
        for (const { globalFilter, value } of this.favoriteRecordMap[favoriteId].favoriteFilters) {
            const currentValue = getters.getGlobalFilterValue(globalFilter.id);
            const favoriteValue = normalizeValue(globalFilter, value);
            if (!deepEqual(currentValue, favoriteValue)) {
                filters.push({
                    filterId: globalFilter.id,
                    value: favoriteValue,
                });
            }
        }
        if (!filters.length) {
            this._refreshFacets();
            return;
        }
        this.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
    }

    _clearFavoriteFilters(favoriteId) {
        this.activeFavoriteId = undefined;

        // Deactivate favorite: clear only filters still matching its default values,
        // keep user-overridden filters unchanged
        const getters = this.spreadsheetModel.getters;
        const favoriteMap = this._getFavoriteMap(favoriteId);
        const filters = [];
        for (const filter of getters.getGlobalFilters()) {
            const currentValue = normalizeValue(filter, getters.getGlobalFilterValue(filter.id));
            const favoriteValue = normalizeValue(filter, favoriteMap.get(filter.id));
            if (deepEqual(currentValue, favoriteValue) && currentValue !== undefined) {
                // Filter is still sitting at the favorite baseline.
                filters.push({ filterId: filter.id, value: undefined });
            }
        }
        if (!filters.length) {
            this._refreshFacets();
            return;
        }
        this.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
    }
}
