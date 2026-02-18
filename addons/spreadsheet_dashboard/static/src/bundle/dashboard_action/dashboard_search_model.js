import { reactive } from "@odoo/owl";
import {
    getDefaultValue,
    getFacetInfo,
    isEmptyFilterValue,
} from "@spreadsheet/global_filters/helpers";
import { user } from "@web/core/user";
import { deepCopy, deepEqual } from "@web/core/utils/objects";

export function serializeFavoriteFilters(filterNodes) {
    const serialized = {};
    for (const { globalFilter, value } of filterNodes) {
        if (!isEmptyFilterValue(globalFilter, value)) {
            serialized[globalFilter.id] = value;
        }
    }
    return serialized;
}

export function deserializeFavoriteFilters(getters, serializedFilters) {
    return getters.getGlobalFilters().map((gf) => ({
        globalFilter: gf,
        value: serializedFilters[gf.id]
            ? { ...serializedFilters[gf.id] }
            : getDefaultValue(gf.type),
    }));
}

function hasFavoriteChanged(oldFilters, newFilters) {
    const oldList = Object.values(oldFilters);
    const newList = Object.values(newFilters);
    for (let i = 0; i < newList.length; i++) {
        if (!deepEqual(oldList[i].value, newList[i].value)) {
            return true;
        }
    }
    return false;
}

function buildFavoriteFacet(localId, label) {
    return {
        id: localId,
        type: "favorite",
        icon: "fa fa-star",
        values: [label],
    };
}

export class DashboardSearchModel {
    constructor(env, orm, spreadsheetModel) {
        this.env = env;
        this.orm = orm;
        this.spreadsheetModel = spreadsheetModel;

        this.state = reactive({
            isLoading: false,
            facets: [],
        });
    }

    async loadFavoritesForDashboard(dashboardId) {
        this.state.isLoading = true;
        this.activeFavoriteId = undefined;
        this.favoriteRecordMap = {};
        this.firstDateFilter = undefined;
        this.activeDashboardId = dashboardId;

        const favoriteRecords = await this.orm.call(
            "spreadsheet.dashboard.favorite.filters",
            "get_filters",
            [dashboardId]
        );
        for (const record of favoriteRecords) {
            const favoriteFilters = deserializeFavoriteFilters(
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
                this.activeFavoriteId = record.id;
            }
        }

        await this._refreshFacets();
        this.state.isLoading = false;
    }

    async _refreshFacets() {
        const facets = [];
        const allFilters = [...this.spreadsheetModel.getters.getGlobalFilters()];

        // remove the first date filter from facets
        const idx = allFilters.findIndex((f) => f.type === "date");
        if (idx !== -1) {
            this.firstDateFilter = allFilters.splice(idx, 1)[0];
        }

        if (this.activeFavoriteId) {
            const fav = this.favoriteRecordMap[this.activeFavoriteId];
            this._applyFavorite(fav);
            facets.push(buildFavoriteFacet(fav.id, fav.description));
        } else {
            for (const filter of allFilters) {
                if (!this.spreadsheetModel.getters.isGlobalFilterActive(filter.id)) {
                    continue;
                }

                const value = this.spreadsheetModel.getters.getGlobalFilterValue(filter.id);
                const info = await getFacetInfo(
                    this.env,
                    filter,
                    value,
                    this.spreadsheetModel.getters
                );
                facets.push({
                    id: info.id,
                    type: "field",
                    title: info.title,
                    values: info.values,
                    operator: info.operator,
                    separator: info.separator,
                });
            }
        }
        this.state.facets = facets;
    }

    async createFavoriteRecord(name, isDefault, filterNodes) {
        const payload = {
            name,
            dashboard_id: this.activeDashboardId,
            global_filters: serializeFavoriteFilters(filterNodes),
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
        this.activeFavoriteId = serverSideId;

        this._refreshFacets();
        return serverSideId;
    }

    toggleFavorite(localId) {
        if (this.activeFavoriteId === localId) {
            this.activeFavoriteId = undefined;
            this._clearAllActiveGlobalFilters();
            this._refreshFacets();
            return this.spreadsheetModel.getters.getGlobalFilters().map((f) => ({
                globalFilter: f,
                value: getDefaultValue(f.type),
            }));
        }

        // Switch favorite
        this.activeFavoriteId = localId;
        const fav = this.favoriteRecordMap[localId];
        this._applyFavorite(fav);
        this.state.facets = [buildFavoriteFacet(localId, fav.description)];
        return deepCopy(fav.favoriteFilters);
    }

    clearFilter(filterId) {
        if (this.activeFavoriteId === filterId) {
            this.activeFavoriteId = undefined;
            this._clearAllActiveGlobalFilters();
            this._refreshFacets();
            return;
        }

        // Clearing a normal field filter
        this.spreadsheetModel.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filterId });
        this.state.facets = this.state.facets.filter((f) => f.id !== filterId);
    }

    handleManualFilterConfirm(updatedFilters) {
        if (this.activeFavoriteId) {
            const current = this.favoriteRecordMap[this.activeFavoriteId].favoriteFilters;
            if (!updatedFilters || hasFavoriteChanged(current, updatedFilters)) {
                this.activeFavoriteId = undefined;
            }
        }
        this._refreshFacets();
    }

    getFavoriteList(predicate) {
        return Object.values(this.favoriteRecordMap)
            .map((fav) => ({
                ...fav,
                isActive: fav.id === this.activeFavoriteId,
            }))
            .filter((f) => !predicate || predicate(f));
    }

    _applyFavorite(favorite) {
        for (const { globalFilter, value } of favorite.favoriteFilters) {
            const current = this.spreadsheetModel.getters.getGlobalFilterValue(globalFilter.id);
            if (!deepEqual(current, value)) {
                this.spreadsheetModel.dispatch("SET_GLOBAL_FILTER_VALUE", {
                    id: globalFilter.id,
                    value: isEmptyFilterValue(globalFilter, value) ? undefined : value,
                });
            }
        }
    }

    _clearAllActiveGlobalFilters() {
        const filters = this.spreadsheetModel.getters.getGlobalFilters();
        for (const f of filters) {
            if (this.spreadsheetModel.getters.isGlobalFilterActive(f.id)) {
                this.spreadsheetModel.dispatch("SET_GLOBAL_FILTER_VALUE", { id: f.id });
            }
        }
    }
}
