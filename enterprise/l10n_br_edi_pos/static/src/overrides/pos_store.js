import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    editPartnerContext(partner) {
        // Set some default fields when creating a new customer.
        const res = super.editPartnerContext(partner);
        if (!this.config.l10n_br_is_nfce || partner) {
            return res;
        }

        return {
            ...res,
            default_l10n_br_tax_regime: "individual",
            default_l10n_br_taxpayer: "non",
            default_l10n_br_activity_sector: "finalConsumer",
        };
    },

    orderDetailsProps(order) {
        // If the user clicks the "Retry EDI" button and closes the dialog without clicking the "Save" button,
        // the data will be outdated.
        const res = super.orderDetailsProps(order);
        if (this.config.l10n_br_is_nfce) {
            res.onRecordDiscarded = async () => {
                if (order.id) {
                    await this.data.read("pos.order", [order.id]);
                }
            };
        }
        return res;
    },
});
