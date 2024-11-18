odoo.define("l10n_be_pos_sale.models", function (require) {
    "use strict";

    var { PosGlobalState } = require("point_of_sale.models");
    const Registries = require("point_of_sale.Registries");

    const PoSSaleBeGlobalState = (PosGlobalState) =>
        class PoSSaleBeGlobalState extends PosGlobalState {
            async _processData(loadedData) {
                await super._processData(...arguments);
                if (this.company.country && this.company.country.code == "BE") {
                    this.intracom_tax_ids = loadedData["intracom_tax_ids"];
                }
            }
        };
    Registries.Model.extend(PosGlobalState, PoSSaleBeGlobalState);
});
