/** @odoo-module */

import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { _t } from "@web/core/l10n/translation";
import { GraphModel as ChartModel } from "@web/views/graph/graph_model";

export default class ChartDataSource extends OdooViewsDataSource {
    /**
     * @override
     * @param {Object} services Services (see DataSource)
     */
    constructor(services, params) {
        super(services, params);
        this._metaData.measure = params.measure;
        this._metaData.order = params.orderBy ? (params.orderBy.asc ? "ASC" : "DESC") : null;
        this._metaData.groupBy = params.groupBy;
        this._metaData.mode = params.mode;
        this._metaData.fieldAttrs = {};
    }

    /**
     * @protected
     */
    async _load() {
        await super._load();
        this._model = new ChartModel({ _t }, this._metaData, {
            orm: this._orm,
        });
        await this._model.load(this._searchParams);
    }

    getData() {
        if (!this.isReady()) {
            this.load();
            return { datasets: [], labels: [] };
        }
        if (!this._isValid) {
            return { datasets: [], labels: [] };
        }
        return this._model.data;
    }
}
