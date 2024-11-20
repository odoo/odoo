import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { _t } from "@web/core/l10n/translation";
import { SpreadsheetGraphModel } from "./graph_model";

export class ChartDataSource extends OdooViewsDataSource {
    /**
     * @override
     * @param {Object} services Services (see DataSource)
     */
    constructor(services, params) {
        super(services, params);
    }

    /**
     * @protected
     */
    async _load() {
        await super._load();
        const metaData = {
            fieldAttrs: {},
            ...this._metaData,
        };
        this._model = new SpreadsheetGraphModel(
            {
                _t,
            },
            metaData,
            {
                orm: this._orm,
            }
        );
        // force an empty searchParams.groupBy to always use metaData.groupBy.
        // Some existing charts have searchParams.groupBy
        await this._model.load({ ...this._searchParams, groupBy: [] });
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
