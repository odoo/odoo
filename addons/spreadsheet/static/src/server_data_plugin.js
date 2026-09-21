import { registries } from "@odoo/o-spreadsheet";
import { OdooEvaluationPlugin } from "@spreadsheet/plugins";
const { evaluationPluginRegistry } = registries;

export class ServerDataPlugin extends OdooEvaluationPlugin {
    static getters = /** @type {const} */ (["getServerData"]);

    handlers = {
        REFRESH_ALL_DATA_SOURCES: this.onRefreshAllDataSources,
    };

    constructor(config) {
        super(config);
        /** @type {import("@spreadsheet/data_sources/server_data").ServerData} */
        this._serverData = config.custom.odooDataProvider?.serverData;
    }

    onRefreshAllDataSources() {
        this.getServerData().clearCache();
        this.dispatch("EVALUATE_CELLS");
    }

    getServerData() {
        if (!this._serverData) {
            throw new Error(
                "'serverData' is not defined, please make sure a 'OdooDataProvider' instance is provided to the model."
            );
        }
        return this._serverData;
    }
}

evaluationPluginRegistry.add("odooServerData", ServerDataPlugin);
