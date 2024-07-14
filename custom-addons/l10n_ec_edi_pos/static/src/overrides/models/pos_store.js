/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.isEcuadorianCompany()) {
            this.l10n_latam_identification_types = loadedData["l10n_latam.identification.type"];
            this.finalConsumerId = loadedData["final_consumer_id"];
        }
    },
    isEcuadorianCompany() {
        return this.company.country?.code == "EC";
    },
    // @Override
    // For EC, if the partner on the refund was End Consumer we need to allow the user to change it.
    async selectPartner({ missingFields = [] } = {}) {
        if (!this.isEcuadorianCompany()) {
            return super.selectPartner(...arguments);
        }
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return;
        }
        const currentPartner = currentOrder.get_partner();
        if (currentPartner && currentPartner.id === this.finalConsumerId) {
            const { confirmed, payload: newPartner } = await this.showTempScreen("PartnerListScreen", {
                        partner: currentPartner,
            });
            if (confirmed) {
                currentOrder.set_partner(newPartner);
            }
            return;
        }
        return super.selectPartner(...arguments);
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isEcuadorianCompany()) {
            this.to_invoice = true;
            if (!this.partner && this.pos.finalConsumerId) {
                this.partner = this.pos.db.partner_by_id[this.pos.finalConsumerId];
            }
        }
    },
});
