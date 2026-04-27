import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    // @Override
    setup() {
        super.setup(...arguments);

        if (this.company.l10n_co_edi_pos_dian_enabled && !this.partner_id) {
            this.update({ partner_id: this.session._l10n_co_final_consumer_id });
        }
    },
    // @Override
    export_for_printing(baseUrl, headerData) {
        const data = super.export_for_printing(...arguments);

        if (this.company.l10n_co_edi_pos_dian_enabled) {
            data.to_invoice = this.to_invoice;
            data.l10n_co_edi_pos_receipt_data = JSON.parse(this.l10n_co_edi_pos_receipt_data);
            data.headerData.l10n_co_edi_pos = data.l10n_co_edi_pos_receipt_data.header;
        }

        return data;
    },
});
