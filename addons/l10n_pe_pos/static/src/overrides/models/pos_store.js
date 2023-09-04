/** @odoo-module **/

import {PosGlobalState, Order} from "point_of_sale.models";
import Registries from "point_of_sale.Registries";
import {patch} from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "l10n_pe_pos.PosGlobalState", {
    // @Override
    async _processData(loadedData) {
        const _super = this._super.bind(this);
        await Promise.resolve();
        await _super(...arguments);
        if (this.isPeruvianCompany()) {
            this.l10n_latam_identification_types = loadedData["l10n_latam.identification.type"];
            this.consumidorFinalId = loadedData["consumidor_final_id"];
        }
    },
    isPeruvianCompany() {
        if (this.company.country && this.company.country.code == "PE") {
            return true;
        } else {
            return false;
        }
    },
});

const L10nPeOrder = (Order) =>
    class L10nPeOrder extends Order {
        constructor() {
            super(...arguments);
            if (this.pos.isPeruvianCompany()) {
                if (!this.partner) {
                    this.partner = this.pos.db.partner_by_id[this.pos.consumidorFinalId];
                }
            }
        }
    };
Registries.Model.extend(Order, L10nPeOrder);
